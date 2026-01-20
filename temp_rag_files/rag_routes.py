# ====================================================================================================
# RAG API エンドポイント - FastAPIでのRAG機能公開
# ====================================================================================================

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

from services.rag_service import RAGService, RAGQuery, RAGResponse
from services.document_service import Document, DocumentChunk

# APIルーター
router = APIRouter(prefix="/api/rag", tags=["RAG"])

# Pydanticモデル（API入出力用）
class RAGQueryRequest(BaseModel):
    """RAGクエリリクエスト"""
    query: str = Field(..., description="ユーザーの質問", min_length=1)
    user_id: str = Field(..., description="ユーザーID")
    conversation_id: Optional[str] = Field(None, description="会話ID（継続的会話の場合）")
    max_results: int = Field(5, description="最大検索結果数", ge=1, le=20)
    include_metadata: bool = Field(True, description="メタデータを含めるかどうか")

class DocumentChunkResponse(BaseModel):
    """ドキュメントチャンクレスポンス"""
    id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, str]

class RAGQueryResponse(BaseModel):
    """RAGクエリレスポンス"""
    model_config = {"protected_namespaces": ()}
    
    query: str
    answer: str
    relevant_chunks: List[DocumentChunkResponse]
    conversation_id: str
    timestamp: str
    response_metadata: Optional[Dict[str, Any]] = None

class DocumentListResponse(BaseModel):
    """ドキュメント一覧レスポンス"""
    id: str
    filename: str
    title: str
    file_path: str
    metadata: Dict[str, str]
    chunk_count: int
    created_at: str
    updated_at: str

class SearchResponse(BaseModel):
    """検索レスポンス"""
    query: str
    chunks: List[DocumentChunkResponse]
    total_found: int

# RAGサービスのインスタンス
rag_service = RAGService()

# ログ設定
logger = logging.getLogger(__name__)

@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest) -> RAGQueryResponse:
    """
    RAGクエリの実行
    
    ユーザーの質問に対して、ドキュメントを検索して関連情報を元にAIが回答を生成します。
    """
    try:
        logger.info(f"RAGクエリ受信: user={request.user_id}, query={request.query[:50]}...")
        
        # RAGクエリオブジェクトを作成
        rag_query = RAGQuery(
            user_id=request.user_id,
            query=request.query,
            conversation_id=request.conversation_id,
            max_results=request.max_results,
            include_metadata=request.include_metadata
        )
        
        # RAG応答を生成
        rag_response = await rag_service.generate_rag_response(rag_query)
        
        # レスポンス形式に変換
        response = RAGQueryResponse(
            query=rag_response.query,
            answer=rag_response.answer,
            relevant_chunks=[
                DocumentChunkResponse(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    metadata=chunk.metadata
                )
                for chunk in rag_response.relevant_chunks
            ],
            conversation_id=rag_response.conversation_id,
            timestamp=rag_response.timestamp,
            response_metadata=rag_response.metadata
        )
        
        logger.info(f"RAGクエリ成功: conversation={response.conversation_id}")
        return response
        
    except Exception as e:
        logger.error(f"RAGクエリエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG処理でエラーが発生しました: {str(e)}")

@router.get("/documents", response_model=List[DocumentListResponse])
async def get_documents() -> List[DocumentListResponse]:
    """
    利用可能なドキュメント一覧を取得
    
    RAGシステムで検索可能なドキュメントの一覧を返します。
    """
    try:
        logger.info("ドキュメント一覧リクエスト受信")
        
        documents = await rag_service.get_available_documents()
        
        response = [
            DocumentListResponse(
                id=doc.id,
                filename=doc.filename,
                title=doc.title,
                file_path=doc.file_path,
                metadata=doc.metadata,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            for doc in documents
        ]
        
        logger.info(f"ドキュメント一覧返却: {len(response)} documents")
        return response
        
    except Exception as e:
        logger.error(f"ドキュメント一覧取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ドキュメント取得でエラーが発生しました: {str(e)}")

@router.get("/search", response_model=SearchResponse)
async def search_documents(
    query: str,
    max_results: int = 10
) -> SearchResponse:
    """
    ドキュメント検索
    
    AIによる回答生成なしで、関連するドキュメントチャンクのみを検索します。
    """
    try:
        logger.info(f"ドキュメント検索リクエスト: query={query[:50]}...")
        
        chunks = await rag_service.search_documents_only(query, max_results)
        
        response = SearchResponse(
            query=query,
            chunks=[
                DocumentChunkResponse(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    metadata=chunk.metadata
                )
                for chunk in chunks
            ],
            total_found=len(chunks)
        )
        
        logger.info(f"ドキュメント検索完了: {len(chunks)} chunks found")
        return response
        
    except Exception as e:
        logger.error(f"ドキュメント検索エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"検索でエラーが発生しました: {str(e)}")

@router.get("/health")
async def rag_health_check():
    """
    RAGサービスのヘルスチェック
    
    RAGシステムの稼働状況を確認します。
    """
    try:
        # 基本的なサービス初期化チェック
        documents = await rag_service.get_available_documents()
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "documents_loaded": len(documents),
            "services": {
                "document_service": "ok",
                "search_service": "ok",
                "rag_service": "ok"
            }
        }
        
        # Azure OpenAI接続チェック
        if rag_service.openai_client:
            health_status["services"]["azure_openai"] = "connected"
        else:
            health_status["services"]["azure_openai"] = "not_configured"
            health_status["warnings"] = ["Azure OpenAI client not configured"]
        
        logger.info("RAGヘルスチェック完了")
        return JSONResponse(content=health_status)
        
    except Exception as e:
        logger.error(f"RAGヘルスチェックエラー: {str(e)}")
        error_status = {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
        return JSONResponse(content=error_status, status_code=503)

# 診断用エンドポイント（開発環境のみ）
@router.get("/debug/test-query")
async def debug_test_query():
    """
    デバッグ用テストクエリ
    
    開発・テスト用のサンプルクエリです。
    """
    try:
        test_query = RAGQuery(
            user_id="debug_user",
            query="このプロジェクトについて教えて",
            max_results=3
        )
        
        response = await rag_service.generate_rag_response(test_query)
        
        return {
            "test_query": test_query.query,
            "answer": response.answer,
            "chunks_found": len(response.relevant_chunks),
            "timestamp": response.timestamp
        }
        
    except Exception as e:
        logger.error(f"デバッグクエリエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"デバッグクエリでエラーが発生しました: {str(e)}")

# エラーハンドリング用のミドルウェア（アプリレベルで処理するためコメントアウト）
# @router.middleware("http")
# async def rag_middleware(request, call_next):
#     """RAG API用のミドルウェア"""
#     start_time = datetime.now()
#     
#     try:
#         response = await call_next(request)
#         
#         # レスポンス時間をログ出力
#         processing_time = (datetime.now() - start_time).total_seconds()
#         logger.info(f"RAG API処理時間: {processing_time:.3f}s for {request.url.path}")
#         
#         return response
#         
#     except Exception as e:
#         logger.error(f"RAG APIミドルウェアエラー: {str(e)}")
#         raise