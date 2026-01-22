"""
新しいAzure RAG API routes - Azure Blob Storage + Azure AI Search を使用したRAG機能
"""
import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from datetime import datetime

from services.azure_rag_service import AzureRAGService

logger = logging.getLogger(__name__)

# グローバルRAGサービスインスタンス
azure_rag_service = AzureRAGService()

# APIルーター
router = APIRouter(prefix="/api/azure-rag", tags=["Azure RAG"])

# Pydantic models
class RAGQueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    max_results: Optional[int] = 5

class RAGResponse(BaseModel):
    answer: str
    query: str
    relevant_documents: List[Dict[str, Any]]
    context_used: str
    user_id: Optional[str] = None
    timestamp: str

class DocumentUploadResponse(BaseModel):
    success: bool
    message: str
    blob_url: Optional[str] = None
    index_result: Optional[Dict[str, Any]] = None

class FolderProcessResponse(BaseModel):
    success: bool
    message: str
    summary: Dict[str, Any]

@router.on_event("startup")
async def startup_event():
    """サービス開始時の初期化"""
    try:
        logger.info("Azure RAG service startup event triggered")
        # 初期化は遅延実行（必要になった時に実行）
        logger.info("Azure RAG service startup completed")
    except Exception as e:
        logger.error(f"Failed to initialize Azure RAG service: {e}")
        # 開発環境では続行を許可

@router.post("/query", response_model=RAGResponse)
async def query_documents(request: RAGQueryRequest):
    """RAGクエリ実行エンドポイント"""
    try:
        logger.info(f"RAG query received: {request.query}")
        
        # RAG応答を生成
        result = await azure_rag_service.generate_rag_response(
            query=request.query
        )
        
        return RAGResponse(**result)
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"RAG query failed: {str(e)}"
        )

@router.post("/upload-document", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    index_immediately: bool = Form(True)
):
    """ドキュメントアップロード＆インデックス化エンドポイント"""
    try:
        # サポートされているファイル形式をチェック
        supported_extensions = ['.pdf', '.docx', '.doc', '.txt']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in supported_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_extension}. Supported: {supported_extensions}"
            )
        
        # 一時ファイルに保存
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            if index_immediately:
                # インデックス作成（必要に応じて）
                await azure_rag_service.create_search_index()
                
                # ドキュメントをインデックス化
                index_result = await azure_rag_service.index_document(tmp_file_path)
                
                return DocumentUploadResponse(
                    success=True,
                    message=f"Document {file.filename} uploaded and indexed successfully",
                    blob_url=index_result["blob_url"],
                    index_result=index_result
                )
            else:
                # アップロードのみ
                blob_url = await azure_rag_service.upload_document_to_blob(tmp_file_path)
                
                return DocumentUploadResponse(
                    success=True,
                    message=f"Document {file.filename} uploaded successfully",
                    blob_url=blob_url
                )
                
        finally:
            # 一時ファイルを削除
            os.unlink(tmp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document upload failed: {str(e)}"
        )

@router.post("/process-folder", response_model=FolderProcessResponse)
async def process_documents_folder(request: Dict[str, str]):
    """フォルダ内ドキュメント一括処理エンドポイント"""
    try:
        folder_path = request.get("folder_path")
        logger.info(f"Processing documents folder: {folder_path}")
        
        # フォルダが存在するかチェック
        if not os.path.exists(folder_path):
            raise HTTPException(
                status_code=404,
                detail=f"Folder not found: {folder_path}"
            )
        
        # フォルダ内のドキュメントを処理
        summary = await azure_rag_service.process_documents_folder(folder_path)
        
        return FolderProcessResponse(
            success=True,
            message=f"Processed {summary['total_files_processed']} files successfully",
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Folder processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Folder processing failed: {str(e)}"
        )

@router.post("/create-index")
async def create_search_index():
    """検索インデックス作成エンドポイント"""
    try:
        await azure_rag_service.create_search_index()
        return {"success": True, "message": "Search index created successfully", "index_name": azure_rag_service.index_name}
        
    except Exception as e:
        logger.error(f"Index creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Index creation failed: {str(e)}"
        )

@router.get("/search")
async def search_documents(query: str, top_k: int = 5):
    """ドキュメント検索エンドポイント（デバッグ用）"""
    try:
        documents = await azure_rag_service.search_documents(query, top_k)
        return {
            "query": query,
            "documents": documents,
            "count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Document search failed: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # サービスが初期化されているかチェック
        if not azure_rag_service.initialized:
            await azure_rag_service.initialize()
        
        # ヘルスチェック実行
        is_healthy = azure_rag_service.is_healthy()
        
        if is_healthy:
            return {
                "status": "healthy",
                "service": "Azure RAG", 
                "debug_mode": azure_rag_service.debug_mode,
                "timestamp": datetime.now().isoformat(),
                "initialized": azure_rag_service.initialized
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Service is not healthy"
            )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )