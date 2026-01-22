# ====================================================================================================
# ドキュメント管理サービス - アップロード、インデックス作成、RAG統合
# ====================================================================================================

import os
import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
from datetime import datetime

from .azure_rag_service import AzureRAGService, DocumentMetadata
from .document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

class DocumentManager:
    """ドキュメント管理サービス"""
    
    def __init__(self):
        self.rag_service = AzureRAGService()
        self.processor = DocumentProcessor()
        self.data_directory = Path(__file__).parent.parent / "data"
        
    async def initialize(self) -> bool:
        """サービス初期化"""
        try:
            # データディレクトリ作成
            self.data_directory.mkdir(exist_ok=True)
            
            # RAGサービス初期化
            success = await self.rag_service.initialize()
            if not success:
                logger.error("RAGサービス初期化失敗")
                return False
            
            logger.info("DocumentManager初期化完了")
            return True
            
        except Exception as e:
            logger.error(f"DocumentManager初期化失敗: {e}")
            return False
    
    async def upload_document_file(self, file_path: str) -> Dict[str, Any]:
        """単一ファイルをアップロード・処理"""
        try:
            file_path = Path(file_path)
            
            # ドキュメント処理（テキスト抽出・チャンク分割）
            processed_doc = await self.processor.process_document(str(file_path))
            
            # Blob Storageにアップロード
            blob_metadata = await self.rag_service.upload_document(str(file_path))
            
            # TODO: Azure AI Searchインデックスにドキュメント追加
            # await self._add_to_search_index(processed_doc, blob_metadata)
            
            result = {
                "success": True,
                "file_info": {
                    "name": file_path.name,
                    "size": processed_doc["metadata"]["file_size"],
                    "chunks": processed_doc["metadata"]["chunk_count"]
                },
                "blob_metadata": blob_metadata,
                "processing_metadata": processed_doc["metadata"]
            }
            
            logger.info(f"ドキュメントアップロード完了: {file_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"ドキュメントアップロード失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def upload_directory(self, directory_path: str = None) -> Dict[str, Any]:
        """データディレクトリ内の全ファイルをアップロード"""
        if directory_path is None:
            directory_path = str(self.data_directory)
        
        try:
            directory_path = Path(directory_path)
            
            if not directory_path.exists():
                logger.warning(f"ディレクトリが存在しません: {directory_path}")
                return {
                    "success": True,
                    "message": "アップロードするファイルがありません",
                    "uploaded_files": [],
                    "failed_files": []
                }
            
            uploaded_files = []
            failed_files = []
            
            # サポートされているファイルを検索
            supported_exts = self.processor.get_supported_extensions()
            files_to_process = []
            
            for ext in supported_exts:
                files_to_process.extend(directory_path.glob(f"*{ext}"))
                files_to_process.extend(directory_path.glob(f"**/*{ext}"))  # 再帰的検索
            
            if not files_to_process:
                logger.info("アップロードするファイルが見つかりません")
                return {
                    "success": True,
                    "message": "アップロードするファイルが見つかりません",
                    "uploaded_files": [],
                    "failed_files": []
                }
            
            logger.info(f"{len(files_to_process)}個のファイルを処理開始")
            
            # 各ファイルを処理
            for file_path in files_to_process:
                try:
                    result = await self.upload_document_file(str(file_path))
                    if result["success"]:
                        uploaded_files.append({
                            "file_name": file_path.name,
                            "file_path": str(file_path),
                            "metadata": result
                        })
                    else:
                        failed_files.append({
                            "file_name": file_path.name,
                            "file_path": str(file_path),
                            "error": result["error"]
                        })
                except Exception as e:
                    failed_files.append({
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "error": str(e)
                    })
            
            result = {
                "success": True,
                "message": f"処理完了: 成功 {len(uploaded_files)}件, 失敗 {len(failed_files)}件",
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "summary": {
                    "total_files": len(files_to_process),
                    "successful_uploads": len(uploaded_files),
                    "failed_uploads": len(failed_files)
                }
            }
            
            logger.info(f"ディレクトリアップロード完了: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"ディレクトリアップロード失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "uploaded_files": [],
                "failed_files": []
            }
    
    async def search_documents(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """ドキュメント検索"""
        try:
            results = await self.rag_service.search_documents(query, max_results)
            
            # 結果を辞書形式に変換
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.content,
                    "score": result.score,
                    "file_name": result.metadata.file_name,
                    "highlights": result.highlights or []
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"ドキュメント検索失敗: {e}")
            return []
    
    async def generate_rag_response(self, user_id: str, query: str, conversation_id: str = None) -> Dict[str, Any]:
        """RAG応答生成"""
        try:
            from .azure_rag_service import RAGQuery
            
            rag_query = RAGQuery(
                user_id=user_id,
                query=query,
                conversation_id=conversation_id,
                max_results=int(os.getenv("RAG_MAX_SEARCH_RESULTS", "5"))
            )
            
            response = await self.rag_service.generate_rag_response(rag_query)
            
            # 応答を辞書形式に変換
            return {
                "query": response.query,
                "answer": response.answer,
                "conversation_id": response.conversation_id,
                "timestamp": response.timestamp,
                "relevant_documents": [
                    {
                        "content": doc.content,
                        "score": doc.score,
                        "file_name": doc.metadata.file_name,
                        "highlights": doc.highlights or []
                    }
                    for doc in response.relevant_documents
                ],
                "metadata": response.metadata
            }
            
        except Exception as e:
            logger.error(f"RAG応答生成失敗: {e}")
            return {
                "query": query,
                "answer": f"申し訳ございません。エラーが発生しました: {str(e)}",
                "conversation_id": conversation_id or f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "relevant_documents": [],
                "metadata": {"error": str(e)}
            }
    
    def get_data_directory(self) -> str:
        """データディレクトリのパスを取得"""
        return str(self.data_directory)
    
    def get_supported_file_types(self) -> List[str]:
        """サポートされているファイル形式を取得"""
        return self.processor.get_supported_extensions()
    
    async def get_upload_status(self) -> Dict[str, Any]:
        """アップロード状況を取得"""
        try:
            data_dir = self.data_directory
            if not data_dir.exists():
                return {
                    "data_directory": str(data_dir),
                    "exists": False,
                    "file_count": 0,
                    "supported_files": [],
                    "unsupported_files": []
                }
            
            supported_exts = self.processor.get_supported_extensions()
            supported_files = []
            unsupported_files = []
            
            for file_path in data_dir.rglob("*"):
                if file_path.is_file():
                    if file_path.suffix.lower() in supported_exts:
                        supported_files.append({
                            "name": file_path.name,
                            "path": str(file_path.relative_to(data_dir)),
                            "size": file_path.stat().st_size
                        })
                    else:
                        unsupported_files.append({
                            "name": file_path.name,
                            "path": str(file_path.relative_to(data_dir)),
                            "size": file_path.stat().st_size
                        })
            
            return {
                "data_directory": str(data_dir),
                "exists": True,
                "file_count": len(supported_files) + len(unsupported_files),
                "supported_files": supported_files,
                "unsupported_files": unsupported_files,
                "supported_extensions": supported_exts
            }
            
        except Exception as e:
            logger.error(f"アップロード状況取得失敗: {e}")
            return {
                "error": str(e)
            }