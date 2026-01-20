# ====================================================================================================
# ドキュメント管理サービス - RAGシステムの基盤
# ====================================================================================================

import os
import hashlib
from typing import List, Dict, Optional
from pathlib import Path
import asyncio
from dataclasses import dataclass, asdict

@dataclass
class Document:
    """ドキュメントデータモデル"""
    id: str
    filename: str
    title: str
    content: str
    file_path: str
    metadata: Dict[str, str]
    chunk_count: int = 0
    created_at: str = ""
    updated_at: str = ""

@dataclass
class DocumentChunk:
    """ドキュメントチャンクデータモデル"""
    id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, str]

class DocumentService:
    """ドキュメント管理とチャンク化のサービス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.docs_path = self.project_root / "docs"
        self.readme_path = self.project_root / "README.md"
        self.chunk_size = 1000  # 文字数
        self.chunk_overlap = 200  # オーバーラップ
    
    def generate_document_id(self, file_path: str) -> str:
        """ファイルパスからドキュメントIDを生成"""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """チャンクIDを生成"""
        return f"{document_id}_chunk_{chunk_index}"
    
    async def load_project_documents(self) -> List[Document]:
        """プロジェクトドキュメントをロード"""
        documents = []
        
        # README.mdをロード
        if self.readme_path.exists():
            doc = await self._load_markdown_file(self.readme_path)
            if doc:
                documents.append(doc)
        
        # docs/配下のMarkdownファイルをロード
        if self.docs_path.exists():
            for md_file in self.docs_path.glob("*.md"):
                doc = await self._load_markdown_file(md_file)
                if doc:
                    documents.append(doc)
        
        return documents
    
    async def _load_markdown_file(self, file_path: Path) -> Optional[Document]:
        """Markdownファイルをロードしてドキュメントオブジェクトに変換"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # タイトルを抽出（最初のH1ヘッダーまたはファイル名）
            title = self._extract_title(content) or file_path.stem
            
            document_id = self.generate_document_id(str(file_path))
            
            # メタデータ
            metadata = {
                "file_type": "markdown",
                "file_extension": file_path.suffix,
                "file_size": str(len(content)),
                "category": self._categorize_document(file_path.stem)
            }
            
            return Document(
                id=document_id,
                filename=file_path.name,
                title=title,
                content=content,
                file_path=str(file_path),
                metadata=metadata,
                created_at="",  # TODO: 実際のファイル作成日時
                updated_at=""   # TODO: 実際のファイル更新日時
            )
        
        except Exception as e:
            print(f"ファイル読み込みエラー {file_path}: {str(e)}")
            return None
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Markdownコンテンツからタイトルを抽出"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# ') and len(line) > 2:
                return line[2:].strip()
        return None
    
    def _categorize_document(self, filename: str) -> str:
        """ファイル名に基づいてドキュメントをカテゴライズ"""
        filename_lower = filename.lower()
        
        if filename_lower == 'readme':
            return 'プロジェクト概要'
        elif 'architecture' in filename_lower or 'technical' in filename_lower:
            return '技術仕様'
        elif 'implementation' in filename_lower or 'guide' in filename_lower:
            return '実装ガイド'
        elif 'plan' in filename_lower or 'development' in filename_lower:
            return '開発計画'
        else:
            return 'その他'
    
    async def create_document_chunks(self, document: Document) -> List[DocumentChunk]:
        """ドキュメントをチャンクに分割"""
        chunks = []
        content = document.content
        
        # シンプルな文字数ベースのチャンク化
        chunk_index = 0
        start = 0
        
        while start < len(content):
            end = start + self.chunk_size
            
            # オーバーラップを考慮して調整
            if end < len(content):
                # 文の境界で切る
                next_period = content.find('。', end - 100, end + 100)
                next_newline = content.find('\n', end - 100, end + 100)
                
                if next_period != -1 and (next_newline == -1 or next_period < next_newline):
                    end = next_period + 1
                elif next_newline != -1:
                    end = next_newline + 1
            else:
                end = len(content)
            
            chunk_content = content[start:end].strip()
            
            if chunk_content:  # 空でないチャンクのみ追加
                chunk = DocumentChunk(
                    id=self.generate_chunk_id(document.id, chunk_index),
                    document_id=document.id,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    metadata={
                        "document_title": document.title,
                        "document_category": document.metadata.get("category", ""),
                        "chunk_start": str(start),
                        "chunk_end": str(end)
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # 次のチャンクの開始位置（オーバーラップを考慮）
            start = max(start + 1, end - self.chunk_overlap)
        
        # ドキュメントのチャンク数を更新
        document.chunk_count = len(chunks)
        
        return chunks
    
    async def get_all_documents_with_chunks(self) -> tuple[List[Document], List[DocumentChunk]]:
        """全ドキュメントとチャンクを取得"""
        documents = await self.load_project_documents()
        all_chunks = []
        
        for document in documents:
            chunks = await self.create_document_chunks(document)
            all_chunks.extend(chunks)
        
        return documents, all_chunks

# 使用例
async def main():
    """テスト用メイン関数"""
    service = DocumentService()
    documents, chunks = await service.get_all_documents_with_chunks()
    
    print(f"ロードされたドキュメント数: {len(documents)}")
    print(f"生成されたチャンク数: {len(chunks)}")
    
    for doc in documents:
        print(f"- {doc.title} ({doc.chunk_count} chunks)")

if __name__ == "__main__":
    asyncio.run(main())