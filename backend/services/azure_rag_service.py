"""
Azure AI Search + Blob Storage を使用したRAGサービス
PDFやWordドキュメントをBlob Storageにアップロードし、
Blob Indexerを使用してAzure AI Searchでインデックス化
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
from datetime import datetime, timezone

from azure.storage.blob import BlobServiceClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SemanticConfiguration,
    SemanticSearch,
    SemanticField,
    SemanticPrioritizedFields,
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from openai import AsyncAzureOpenAI
from PyPDF2 import PdfReader
from docx import Document as DocxDocument

from utils.key_vault_helper import KeyVaultHelper

logger = logging.getLogger(__name__)

class AzureRAGService:
    """Azure AI Search + Blob Storageを使用したRAGサービス"""
    
    def __init__(self):
        # デバッグモード設定
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        
        # Key Vault Helper の初期化
        self.kv_helper = KeyVaultHelper.get_instance()
        
        # 設定を読み込み
        self.search_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "documents")
        
        # Storage接続設定（Managed Identity優先）
        storage_conn_str_env = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.storage_connection_string = KeyVaultHelper.resolve_env_value(storage_conn_str_env)
        self.storage_account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
        self.storage_container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "documents")
        
        # OpenAI設定
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        
        # RAG設定
        self.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
        self.max_search_results = int(os.getenv("RAG_MAX_SEARCH_RESULTS", "5"))
        
        # 認証設定
        use_managed_identity = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"
        if use_managed_identity:
            self.credential = DefaultAzureCredential()
        else:
            self.credential = AzureKeyCredential(self.search_key) if self.search_key else None
        
        # 初期化フラグ
        self.initialized = False
        
    async def initialize(self):
        """Azure クライアントを初期化"""
        if self.initialized:
            return
        
        try:
            use_managed_identity = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"
            # デバッグモード
            if self.debug_mode:
                logger.info("Debug mode: Skipping Azure service initialization")
                self.initialized = True
                return
            
            # Blob Storage クライアント
            if use_managed_identity:
                # account_url が未設定なら接続文字列から推測
                account_url = self.storage_account_url
                if not account_url and self.storage_connection_string:
                    # 接続文字列内のAccountNameからURLを組み立て
                    import re
                    m = re.search(r"AccountName=([^;]+)", self.storage_connection_string)
                    if m:
                        account_url = f"https://{m.group(1)}.blob.core.windows.net"
                if not account_url:
                    raise ValueError("AZURE_STORAGE_ACCOUNT_URL is required when using Managed Identity")
                self.blob_service_client = BlobServiceClient(account_url=account_url, credential=self.credential)
            else:
                if self.storage_connection_string:
                    self.blob_service_client = BlobServiceClient.from_connection_string(
                        self.storage_connection_string
                    )
                else:
                    raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required")
            
            # Search クライアント
            if not self.search_endpoint:
                raise ValueError("AZURE_SEARCH_SERVICE_ENDPOINT is required")
                
            if not self.credential:
                raise ValueError("Azure Search credentials are required")
                
            self.search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=self.index_name,
                credential=self.credential
            )
            self.search_index_client = SearchIndexClient(
                endpoint=self.search_endpoint,
                credential=self.credential
            )
            
            # OpenAI クライアント
            if not self.openai_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT is required")
                
            use_managed_identity = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"
            if use_managed_identity:
                # Managed Identity用の非同期トークンプロバイダーを作成
                async def get_token_provider():
                    token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
                    return token.token
                
                self.openai_client = AsyncAzureOpenAI(
                    azure_endpoint=self.openai_endpoint,
                    api_version=self.openai_api_version,
                    azure_ad_token_provider=get_token_provider
                )
            else:
                api_key = os.getenv("AZURE_OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("AZURE_OPENAI_API_KEY is required when not using Managed Identity")
                self.openai_client = AsyncAzureOpenAI(
                    api_key=api_key,
                    api_version=self.openai_api_version,
                    azure_endpoint=self.openai_endpoint
                )
            
            self.initialized = True
            logger.info("Azure RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure RAG service: {e}")
            raise
    
    async def upload_document_to_blob(self, file_path: str, blob_name: str = None) -> str:
        """ドキュメントをBlob Storageにアップロード"""
        if not self.initialized:
            await self.initialize()
            
        try:
            if not blob_name:
                blob_name = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
            
            # コンテナがない場合は作成
            container_client = self.blob_service_client.get_container_client(
                self.storage_container_name
            )
            try:
                container_client.create_container()
                logger.info(f"Created container: {self.storage_container_name}")
            except Exception:
                pass  # コンテナが既に存在する場合
            
            # ファイルをアップロード
            blob_client = self.blob_service_client.get_blob_client(
                container=self.storage_container_name,
                blob=blob_name
            )
            
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            
            blob_url = blob_client.url
            logger.info(f"Successfully uploaded {file_path} to {blob_url}")
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload document to blob: {e}")
            raise
    
    def extract_text_from_document(self, file_path: str) -> str:
        """ドキュメントからテキストを抽出"""
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_extension in ['.doc', '.docx']:
                return self._extract_from_docx(file_path)
            elif file_extension == '.txt':
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            raise
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """PDFファイルからテキストを抽出"""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Wordファイルからテキストを抽出"""
        doc = DocxDocument(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """テキストをチャンクに分割"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            if end < text_length:
                # 文の境界で切る
                last_sentence = text.rfind('.', start, end)
                if last_sentence != -1 and last_sentence > start:
                    end = last_sentence + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            
        return chunks
    
    async def create_search_index(self):
        """Azure AI Search インデックスを作成"""
        if not self.initialized:
            await self.initialize()
        
        # デバッグモード
        if self.debug_mode:
            logger.info(f"Debug mode: Skipping search index creation for: {self.index_name}")
            return
            
        try:
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String, analyzer="ja.microsoft"),
                SimpleField(name="source_file", type=SearchFieldDataType.String),
                SimpleField(name="chunk_id", type=SearchFieldDataType.String),
                SimpleField(name="blob_url", type=SearchFieldDataType.String),
                SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset),
            ]
            
            # セマンティック検索設定
            semantic_config = SemanticConfiguration(
                name="default",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")]
                )
            )
            
            semantic_search = SemanticSearch(configurations=[semantic_config])
            
            # インデックス作成
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                semantic_search=semantic_search
            )
            
            self.search_index_client.create_or_update_index(index)
            logger.info(f"Successfully created/updated search index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to create search index: {e}")
            raise
    
    async def index_document(self, file_path: str) -> Dict[str, Any]:
        """ドキュメントをインデックスに追加"""
        if not self.initialized:
            await self.initialize()
            
        try:
            # ドキュメントをBlob Storageにアップロード
            blob_url = await self.upload_document_to_blob(file_path)
            
            # テキストを抽出
            text = self.extract_text_from_document(file_path)
            
            # テキストをチャンクに分割
            chunks = self.chunk_text(text)
            
            # 検索ドキュメントを作成
            documents = []
            source_file = os.path.basename(file_path)
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{source_file}_{i}_{uuid.uuid4()}"
                document = {
                    "id": doc_id,
                    "content": chunk,
                    "source_file": source_file,
                    "chunk_id": str(i),
                    "blob_url": blob_url,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                documents.append(document)
            
            # ドキュメントをアップロード
            result = self.search_client.upload_documents(documents)
            
            logger.info(f"Successfully indexed {len(documents)} chunks from {source_file}")
            
            return {
                "source_file": source_file,
                "blob_url": blob_url,
                "chunks_count": len(documents),
                "documents": documents
            }
            
        except Exception as e:
            logger.error(f"Failed to index document {file_path}: {e}")
            raise
    
    async def search_documents(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """ドキュメントを検索"""
        if not self.initialized:
            await self.initialize()
            
        if top_k is None:
            top_k = self.max_search_results
        
        # デバッグモード
        if self.debug_mode:
            logger.info(f"Debug mode: Returning mock search results for query: {query}")
            return [
                {
                    "content": f"Mock document 1 content for: {query}",
                    "filename": "mock_document_1.pdf",
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "score": 0.9
                },
                {
                    "content": f"Mock document 2 content for: {query}",
                    "filename": "mock_document_2.docx",
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "score": 0.85
                }
            ]
            
        try:
            # セマンティック検索を実行
            results = self.search_client.search(
                search_text=query,
                top=top_k,
                query_type="simple",
                select="content,filename,uploaded_at"
            )
            
            documents = []
            for result in results:
                documents.append({
                    "content": result["content"],
                    "filename": result["filename"],
                    "uploaded_at": result.get("uploaded_at"),
                    "score": result.get("@search.score", 0)
                })
            
            logger.info(f"Found {len(documents)} documents for query: {query}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to search documents: {e}")
            raise
    
    async def generate_rag_response(self, query: str, user_id: str = None) -> Dict[str, Any]:
        """RAGを使用して応答を生成"""
        if not self.initialized:
            await self.initialize()
        
        # デバッグモード
        if self.debug_mode:
            logger.info(f"Debug mode: Generating mock response for query: {query}")
            return {
                "answer": f"[デバッグモード] '{query}' に関する情報：\n\n" \
                          "現在はデバッグモードで動作しており、実際のAI応答は生成されません。\n" \
                          "実際のAzureサービスに接続するには、.envファイルのDEBUG=falseに設定し、" \
                          "適切なAzure OpenAI、Storage、AI Searchの設定を行ってください。",
                "query": query,
                "relevant_documents": [],
                "context_used": "",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        try:
            # 関連ドキュメントを検索
            relevant_docs = await self.search_documents(query)
            
            # コンテキストを構築
            context = "\n\n".join([
                f"[出典: {doc['filename']}]\n{doc['content']}" 
                for doc in relevant_docs
            ])
            
            # システムプロンプトを構築
            system_prompt = f"""あなたは親切なAIアシスタントです。以下の情報を基にして、ユーザーの質問に丁寧に答えてください。

提供された情報:
{context}

回答の際は：
1. 提供された情報に基づいて回答してください
2. 情報が不足している場合は、その旨を伝えてください
3. 出典となるドキュメント名を可能な限り含めてください
4. 自然で読みやすい日本語で回答してください
5. **重要**：回答は人がそのまま読み上げることを前提としてください
   - Markdownの記号（#、**、-、など）は使用しないでください
   - 段落分けは改行で行い、記号は使わないでください
   - 箇条書きは「1つ目は～」「2つ目は～」のような自然な日本語で表現してください
   - 読み上げに最適な、流暢で自然な文体を使用してください
"""

            # OpenAI APIで応答を生成
            response = await self.openai_client.chat.completions.create(
                model=self.openai_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            # 結果を返す
            result = {
                "answer": answer,
                "query": query,
                "relevant_documents": relevant_docs,
                "context_used": context,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Generated RAG response for query: {query}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate RAG response: {e}")
            raise
    
    async def process_documents_folder(self, folder_path: str) -> Dict[str, Any]:
        """フォルダ内の全ドキュメントを処理"""
        if not self.initialized:
            await self.initialize()
            
        try:
            folder = Path(folder_path)
            if not folder.exists():
                raise FileNotFoundError(f"Folder not found: {folder_path}")
            
            supported_extensions = {'.pdf', '.docx', '.doc', '.txt'}
            files_processed = []
            files_failed = []
            
            # インデックスを作成（存在しない場合）
            await self.create_search_index()
            
            # フォルダ内のファイルを処理
            for file_path in folder.glob('**/*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    try:
                        result = await self.index_document(str(file_path))
                        files_processed.append({
                            "file_path": str(file_path),
                            "result": result
                        })
                        logger.info(f"Successfully processed: {file_path}")
                        
                    except Exception as e:
                        files_failed.append({
                            "file_path": str(file_path),
                            "error": str(e)
                        })
                        logger.error(f"Failed to process {file_path}: {e}")
            
            summary = {
                "total_files_processed": len(files_processed),
                "total_files_failed": len(files_failed),
                "files_processed": files_processed,
                "files_failed": files_failed,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Folder processing complete. Processed: {len(files_processed)}, Failed: {len(files_failed)}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to process documents folder: {e}")
            raise
    
    def is_healthy(self) -> bool:
        """サービスのヘルスチェック"""
        if self.debug_mode:
            logger.info("Debug mode: Health check always returns True")
            return True
        
        return (
            self.initialized and 
            self.storage_connection_string is not None and 
            self.search_endpoint is not None and 
            self.openai_endpoint is not None
        )