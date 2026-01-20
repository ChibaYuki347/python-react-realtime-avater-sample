# ====================================================================================================
# RAGサービス - 検索拡張生成システムの実装
# ====================================================================================================

import os
import json
import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from datetime import datetime
from pathlib import Path

# OpenAI SDK
from openai import AsyncAzureOpenAI

# 自作サービス
from .document_service import DocumentService, Document, DocumentChunk

@dataclass
class RAGQuery:
    """RAGクエリデータモデル"""
    user_id: str
    query: str
    conversation_id: Optional[str] = None
    max_results: int = 5
    include_metadata: bool = True

@dataclass
class RAGResponse:
    """RAG応答データモデル"""
    query: str
    answer: str
    relevant_chunks: List[DocumentChunk]
    conversation_id: str
    timestamp: str
    metadata: Dict[str, any] = None

class SimpleEmbeddingService:
    """シンプルな検索サービス（後でAzure AI Searchに置き換え予定）"""
    
    def __init__(self):
        self.documents: List[Document] = []
        self.chunks: List[DocumentChunk] = []
        self._initialized = False
    
    async def initialize(self):
        """サービス初期化"""
        if self._initialized:
            return
        
        doc_service = DocumentService()
        self.documents, self.chunks = await doc_service.get_all_documents_with_chunks()
        self._initialized = True
        logging.info(f"RAG検索サービス初期化完了: {len(self.documents)} documents, {len(self.chunks)} chunks")
    
    async def search_chunks(self, query: str, max_results: int = 5) -> List[DocumentChunk]:
        """キーワードベースの簡易検索"""
        await self.initialize()
        
        query_lower = query.lower()
        results = []
        
        for chunk in self.chunks:
            # シンプルなキーワードマッチング
            content_lower = chunk.content.lower()
            
            # クエリに含まれる単語の出現回数をスコアとする
            score = 0
            for word in query_lower.split():
                score += content_lower.count(word)
            
            if score > 0:
                results.append((chunk, score))
        
        # スコア順にソート
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 上位結果を返す
        return [chunk for chunk, score in results[:max_results]]

class RAGService:
    """RAG (Retrieval Augmented Generation) メインサービス"""
    
    def __init__(self):
        # Azure OpenAI設定
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_key = os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4-1")
        self.use_managed_identity = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"
        
        self.logger = logging.getLogger(__name__)
        
        # OpenAIクライアント
        self.openai_client = None
        if self.azure_openai_endpoint:
            try:
                if self.azure_openai_key and not self.use_managed_identity:
                    # API Key認証
                    self.openai_client = AsyncAzureOpenAI(
                        azure_endpoint=self.azure_openai_endpoint,
                        api_key=self.azure_openai_key,
                        api_version="2024-05-01-preview"
                    )
                    self.logger.info(f"RAG: Azure OpenAI クライアント初期化成功 (API Key): {self.azure_openai_endpoint}")
                else:
                    # Managed Identity認証
                    from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
                    
                    credential = AsyncDefaultAzureCredential()
                    
                    async def get_token():
                        token = await credential.get_token("https://cognitiveservices.azure.com/.default")
                        return token.token
                    
                    self.openai_client = AsyncAzureOpenAI(
                        azure_ad_token_provider=get_token,
                        api_version="2024-05-01-preview",
                        azure_endpoint=self.azure_openai_endpoint
                    )
                    self.logger.info(f"RAG: Azure OpenAI クライアント初期化成功 (Managed Identity): {self.azure_openai_endpoint}")
            except Exception as e:
                self.logger.error(f"RAG: Azure OpenAI クライアント初期化エラー: {str(e)}")
        else:
            self.logger.warning("RAG: AZURE_OPENAI_ENDPOINT が設定されていません")
        
        # 検索サービス
        self.search_service = SimpleEmbeddingService()
    
    async def generate_rag_response(self, rag_query: RAGQuery) -> RAGResponse:
        """RAG応答を生成"""
        try:
            # 1. 関連ドキュメントを検索
            relevant_chunks = await self.search_service.search_chunks(
                rag_query.query, 
                rag_query.max_results
            )
            
            # 2. GPT-4.1を使って応答を生成
            answer = await self._generate_answer_with_context(
                rag_query.query, 
                relevant_chunks
            )
            
            # 3. RAG応答を構築
            response = RAGResponse(
                query=rag_query.query,
                answer=answer,
                relevant_chunks=relevant_chunks,
                conversation_id=rag_query.conversation_id or self._generate_conversation_id(),
                timestamp=datetime.now().isoformat(),
                metadata={
                    "chunks_used": len(relevant_chunks),
                    "model": self.azure_openai_deployment,
                    "user_id": rag_query.user_id
                }
            )
            
            self.logger.info(f"RAG応答生成成功: {rag_query.user_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"RAG応答生成エラー: {str(e)}")
            # エラー時はデフォルト応答
            return RAGResponse(
                query=rag_query.query,
                answer="申し訳ありませんが、回答を生成できませんでした。別の質問をお試しください。",
                relevant_chunks=[],
                conversation_id=rag_query.conversation_id or self._generate_conversation_id(),
                timestamp=datetime.now().isoformat(),
                metadata={"error": str(e)}
            )
    
    async def _generate_answer_with_context(self, query: str, chunks: List[DocumentChunk]) -> str:
        """コンテキストを使ってGPT-4.1で応答生成"""
        if not self.openai_client:
            # 開発環境用のモック応答
            if not chunks:
                return "申し訳ありませんが、関連する情報が見つかりませんでした。Azure OpenAI接続が設定されていないため、モック応答を返しています。"
            
            # チャンクの内容に基づいた簡易応答
            context_summary = "\n".join([f"• {chunk.content[:150]}..." for chunk in chunks[:3]])
            return f"""
【開発環境での RAG検索結果】

「{query}」に関する情報をプロジェクトドキュメントから検索しました：

{context_summary}

📋 **検索結果詳細**:
- 見つかったチャンク数: {len(chunks)}
- 主要ドキュメント: {', '.join(set([chunk.metadata.get('document_title', '不明')[:20] for chunk in chunks[:3]]))}
- 関連カテゴリ: {', '.join(set([chunk.metadata.get('document_category', '') for chunk in chunks[:3] if chunk.metadata.get('document_category')]))}

💡 **完全なAI応答を得るには**: Azure OpenAI サービス接続が必要です。現在は検索機能のみ動作中です。

より詳しい情報が必要でしたら、具体的な質問をお試しください。
            """.strip()
        
        if not chunks:
            return "申し訳ありませんが、関連する情報が見つかりませんでした。別の質問をお試しください。"
        
        # コンテキストを構築
        context = "\n\n".join([
            f"【{chunk.metadata.get('document_title', '不明')}】\n{chunk.content}"
            for chunk in chunks
        ])
        
        # プロンプト構築
        system_prompt = """
あなたはPythonとReactを使ったリアルタイムアバターアプリのアシスタントです。
以下の技術仕様と実装ガイドに基づいて、正確で具体的な回答を提供してください。

重要な指針:
1. 提供されたコンテキスト情報を基に回答する
2. Azure Speech Service、FastAPI、Reactの技術的詳細に精通している
3. 実装に役立つ具体的なコードやアプローチを提案する
4. コンテキストに情報がない場合は、そのことを明確に伝える
5. 回答は日本語で、技術的に正確で理解しやすく説明する
"""
        
        user_prompt = f"""
以下のコンテキスト情報に基づいて質問に答えてください：

【コンテキスト情報】
{context}

【質問】
{query}

【回答の指針】
- コンテキスト情報を活用して具体的に回答する
- 技術的な内容は実装例やコードスニペットを含める
- 関連する Azure サービスの設定や使い方があれば説明する
- 情報が不足している場合は、どのような情報が必要かを提案する
"""
        
        try:
            # Azure OpenAI APIを呼び出し
            response = await self.openai_client.chat.completions.create(
                model=self.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"OpenAI API呼び出しエラー: {str(e)}")
            return f"回答生成中にエラーが発生しました: {str(e)}"
    
    def _generate_conversation_id(self) -> str:
        """会話IDを生成"""
        import uuid
        return str(uuid.uuid4())
    
    async def get_available_documents(self) -> List[Document]:
        """利用可能なドキュメント一覧を取得"""
        await self.search_service.initialize()
        return self.search_service.documents
    
    async def search_documents_only(self, query: str, max_results: int = 10) -> List[DocumentChunk]:
        """ドキュメント検索のみ（GPT応答なし）"""
        return await self.search_service.search_chunks(query, max_results)

# テスト用関数
async def test_rag_service():
    """RAGサービスのテスト"""
    rag_service = RAGService()
    
    # テストクエリ
    test_queries = [
        "このプロジェクトの技術構成について教えて",
        "Azure Speech Serviceの設定方法は？",
        "Reactでアバターを表示する方法",
        "FastAPIのAPIエンドポイントについて"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"質問: {query}")
        print(f"{'='*50}")
        
        rag_query = RAGQuery(
            user_id="test_user",
            query=query,
            max_results=3
        )
        
        response = await rag_service.generate_rag_response(rag_query)
        print(f"回答: {response.answer}")
        print(f"使用されたチャンク数: {len(response.relevant_chunks)}")

if __name__ == "__main__":
    asyncio.run(test_rag_service())