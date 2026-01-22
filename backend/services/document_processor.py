# ====================================================================================================
# ドキュメント処理サービス - PDF、Word等の文書をテキスト抽出・処理
# ====================================================================================================

import os
import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
from datetime import datetime

# Document processing libraries
import PyPDF2
from docx import Document as DocxDocument
import aiofiles

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """ドキュメント処理サービス"""
    
    def __init__(self):
        self.supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md'}
    
    async def process_document(self, file_path: str) -> Dict[str, Any]:
        """ドキュメントを処理してテキストを抽出"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
        
        if file_path.suffix.lower() not in self.supported_extensions:
            raise ValueError(f"サポートされていないファイル形式: {file_path.suffix}")
        
        try:
            text_content = await self._extract_text(file_path)
            
            # チャンク分割
            chunks = self._split_into_chunks(text_content)
            
            # メタデータ作成
            metadata = {
                "file_name": file_path.name,
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "file_type": file_path.suffix.lower(),
                "processed_time": datetime.now().isoformat(),
                "content_length": len(text_content),
                "chunk_count": len(chunks)
            }
            
            return {
                "text_content": text_content,
                "chunks": chunks,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"ドキュメント処理失敗 {file_path}: {e}")
            raise
    
    async def _extract_text(self, file_path: Path) -> str:
        """ファイル形式に応じてテキストを抽出"""
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return await self._extract_from_pdf(file_path)
        elif extension in ['.docx', '.doc']:
            return await self._extract_from_docx(file_path)
        elif extension in ['.txt', '.md']:
            return await self._extract_from_text(file_path)
        else:
            raise ValueError(f"未対応のファイル形式: {extension}")
    
    async def _extract_from_pdf(self, file_path: Path) -> str:
        """PDFからテキストを抽出"""
        def extract_pdf_sync():
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_parts = []
                
                for page in reader.pages:
                    text_parts.append(page.extract_text())
                
                return '\\n'.join(text_parts)
        
        # 同期処理を別スレッドで実行
        return await asyncio.get_event_loop().run_in_executor(None, extract_pdf_sync)
    
    async def _extract_from_docx(self, file_path: Path) -> str:
        """Word文書からテキストを抽出"""
        def extract_docx_sync():
            doc = DocxDocument(file_path)
            text_parts = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            return '\\n'.join(text_parts)
        
        # 同期処理を別スレッドで実行
        return await asyncio.get_event_loop().run_in_executor(None, extract_docx_sync)
    
    async def _extract_from_text(self, file_path: Path) -> str:
        """テキストファイルから内容を読み込み"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            return await file.read()
    
    def _split_into_chunks(self, text: str, chunk_size: int = None, overlap: int = None) -> List[Dict[str, Any]]:
        """テキストをチャンクに分割"""
        if chunk_size is None:
            chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
        if overlap is None:
            overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
        
        chunks = []
        start = 0
        chunk_id = 1
        
        while start < len(text):
            end = start + chunk_size
            
            # チャンクの境界を調整（単語の境界で分割）
            if end < len(text):
                # 次の空白文字を探す
                while end > start and text[end] not in [' ', '\\n', '\\t', '。', '．', '！', '？']:
                    end -= 1
                
                # 適切な区切りが見つからない場合は元のサイズで分割
                if end <= start:
                    end = start + chunk_size
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk = {
                    "id": chunk_id,
                    "content": chunk_text,
                    "start_pos": start,
                    "end_pos": end,
                    "length": len(chunk_text)
                }
                chunks.append(chunk)
                chunk_id += 1
            
            # 次の開始位置（オーバーラップを考慮）
            start = max(start + 1, end - overlap)
        
        return chunks
    
    async def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """ディレクトリ内の全文書を処理"""
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"有効なディレクトリではありません: {directory_path}")
        
        processed_documents = []
        
        # サポートされているファイルを検索
        for file_path in directory_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                try:
                    logger.info(f"処理中: {file_path}")
                    result = await self.process_document(str(file_path))
                    processed_documents.append(result)
                    logger.info(f"処理完了: {file_path} ({result['metadata']['chunk_count']}チャンク)")
                except Exception as e:
                    logger.error(f"処理失敗: {file_path} - {e}")
                    continue
        
        logger.info(f"ディレクトリ処理完了: {len(processed_documents)}ファイル処理")
        return processed_documents
    
    def get_supported_extensions(self) -> List[str]:
        """サポートされているファイル拡張子を取得"""
        return list(self.supported_extensions)