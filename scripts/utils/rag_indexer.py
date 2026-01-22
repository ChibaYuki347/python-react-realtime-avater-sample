"""
Azure RAG インデキシング・コアロジック

このモジュールは、ドキュメント処理とAzure AI Searchインデックス作成の
コア機能を提供します。Managed Identity認証を使用しています。
"""

import logging
import requests
import json
from typing import Optional
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
)


logger = logging.getLogger(__name__)


class RAGIndexer:
    """
    RAGインデックス作成とドキュメント管理を担当するクラス
    
    Managed Identity による認証を使用して Azure リソースにアクセスします。
    """

    def __init__(
        self,
        search_service_endpoint: str,
        search_service_key: Optional[str] = None,
        storage_account_url: Optional[str] = None,
        storage_account_key: Optional[str] = None,
        use_managed_identity: bool = True,
    ):
        """
        RAGIndexerを初期化します
        
        Args:
            search_service_endpoint: Azure Search Service のエンドポイント URL
            search_service_key: Search Service のアクセスキー（MIを使わない場合）
            storage_account_url: Blob Storage のアカウント URL
            storage_account_key: Blob Storage のアクセスキー（MIを使わない場合）
            use_managed_identity: Managed Identity を使用するかどうか（推奨: True）
        """
        self.search_service_endpoint = search_service_endpoint
        self.storage_account_url = storage_account_url
        self.use_managed_identity = use_managed_identity
        self.credential = None

        # 認証方式の設定
        if use_managed_identity:
            logger.info("✓ Managed Identity 認証を使用します")
            self.credential = DefaultAzureCredential()
        else:
            logger.warning("⚠ API キー認証を使用します（本番環境では推奨されません）")
            self.credential = None

        # Azure Search クライアント初期化
        try:
            if use_managed_identity:
                self.search_index_client = SearchIndexClient(
                    endpoint=search_service_endpoint, credential=self.credential
                )
            else:
                self.search_index_client = SearchIndexClient(
                    endpoint=search_service_endpoint, api_key=search_service_key
                )
            logger.info("✓ Search Index Client が初期化されました")
        except Exception as e:
            logger.error(f"❌ Search Index Client 初期化エラー: {e}")
            raise

        # Azure Blob Storage クライアント初期化
        try:
            if use_managed_identity and storage_account_url:
                self.blob_service_client = BlobServiceClient(
                    account_url=storage_account_url, credential=self.credential
                )
            elif storage_account_url and storage_account_key:
                self.blob_service_client = BlobServiceClient(
                    account_url=storage_account_url, credential=storage_account_key
                )
            else:
                self.blob_service_client = None
                logger.warning("⚠ Blob Storage Client は初期化されていません")
        except Exception as e:
            logger.error(f"❌ Blob Storage Client 初期化エラー: {e}")
            raise

    def create_container(self, container_name: str) -> bool:
        """
        Blob Storage にコンテナを作成します（存在しない場合のみ）
        
        Args:
            container_name: 作成するコンテナ名
        
        Returns:
            成功時: True、失敗時: False
        """
        if not self.blob_service_client:
            logger.error("❌ Blob Storage Client が初期化されていません")
            return False

        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )
            container_client.get_container_properties()
            logger.info(f"✓ コンテナ '{container_name}' は既に存在します")
            return True
        except Exception:
            # コンテナが存在しないので作成
            try:
                self.blob_service_client.create_container(container_name)
                logger.info(f"✓ コンテナ '{container_name}' を作成しました")
                return True
            except Exception as e:
                logger.error(f"❌ コンテナ作成エラー: {e}")
                return False

    def create_index(self, index_name: str) -> None:
        """
        Azure AI Search にインデックスを作成します
        
        Args:
            index_name: 作成するインデックスの名前
        """
        try:
            # インデックスが既に存在するかチェック
            try:
                self.search_index_client.get_index(index_name)
                logger.info(f"✓ インデックス '{index_name}' は既に存在します")
                return
            except Exception:
                pass

            # 新しいインデックスを定義
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(
                    name="content",
                    type=SearchFieldDataType.String,
                    analyzer_name="ja.microsoft",
                ),
                SimpleField(
                    name="filename",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    searchable=True,
                ),
                SimpleField(
                    name="metadata_storage_path",
                    type=SearchFieldDataType.String,
                    retrievable=True,
                ),
                SimpleField(
                    name="metadata_storage_name",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=True,
                ),
            ]

            index = SearchIndex(name=index_name, fields=fields)
            self.search_index_client.create_index(index)
            logger.info(f"✓ インデックス '{index_name}' が作成されました")

        except Exception as e:
            logger.error(f"❌ インデックス作成エラー: {e}")
            raise

    def upload_document(
        self,
        container_name: str,
        blob_name: str,
        file_path: str,
    ) -> bool:
        """
        ドキュメントをBlob Storageにアップロードします
        
        Args:
            container_name: アップロード先コンテナ名
            blob_name: Blob オブジェクト名
            file_path: アップロード対象ファイルのパス
        
        Returns:
            アップロード成功時: True、失敗時: False
        """
        if not self.blob_service_client:
            logger.error("❌ Blob Storage Client が初期化されていません")
            return False

        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )

            with open(file_path, "rb") as data:
                container_client.upload_blob(blob_name, data, overwrite=True)

            logger.info(f"✓ ドキュメント '{blob_name}' をアップロードしました")
            return True

        except FileNotFoundError:
            logger.error(f"❌ ファイルが見つかりません: {file_path}")
            return False
        except Exception as e:
            logger.error(f"❌ アップロードエラー: {e}")
            return False

    def batch_upload_documents(
        self, container_name: str, folder_path: str, extensions: list = None
    ) -> dict:
        """
        フォルダ内のドキュメントを一括アップロードします
        
        Args:
            container_name: アップロード先コンテナ名
            folder_path: ドキュメントフォルダのパス
            extensions: アップロード対象拡張子リスト（デフォルト: ['.txt', '.pdf', '.docx']）
        
        Returns:
            処理結果辞書 {"uploaded": 成功件数, "failed": 失敗件数, "skipped": スキップ件数}
        """
        if extensions is None:
            extensions = [".txt", ".pdf", ".docx"]

        results = {"uploaded": 0, "failed": 0, "skipped": 0}
        folder = Path(folder_path)

        if not folder.exists():
            logger.error(f"❌ フォルダが見つかりません: {folder_path}")
            return results

        for file_path in folder.rglob("*"):
            if file_path.is_dir():
                continue

            if file_path.suffix.lower() not in extensions:
                results["skipped"] += 1
                continue

            blob_name = file_path.relative_to(folder).as_posix()
            if self.upload_document(container_name, blob_name, str(file_path)):
                results["uploaded"] += 1
            else:
                results["failed"] += 1

        return results

    def create_data_source_and_indexer(
        self, index_name: str, container_name: str, storage_account_name: str
    ) -> bool:
        """
        Azure Search REST API で DataSource と Indexer を作成します
        
        Args:
            index_name: インデックス名
            container_name: Blob コンテナ名
            storage_account_name: Storage Account 名
        
        Returns:
            成功時: True、失敗時: False
        """
        try:
            # Azure Search のベース URL
            search_service_name = self.search_service_endpoint.split("//")[1].split(".")[0]
            api_version = "2024-07-01"
            
            # アクセストークンを取得
            token = self.credential.get_token("https://search.azure.com/.default")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token.token}"
            }
            
            logger.info("🔧 DataSource を作成中...")
            
            # DataSource 作成リクエスト
            data_source_url = f"{self.search_service_endpoint}/datasources/blob-documents-source?api-version={api_version}"
            data_source_payload = {
                "name": "blob-documents-source",
                "type": "azureblob",
                "credentials": {
                    "connectionString": f"ResourceId=/subscriptions/{self._get_subscription_id()}/resourceGroups/{self._get_resource_group()}/providers/Microsoft.Storage/storageAccounts/{storage_account_name};"
                },
                "container": {
                    "name": container_name
                },
                "dataChangeDetectionPolicy": {
                    "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy",
                    "highWaterMarkColumnName": "metadata_storage_last_modified"
                }
            }
            
            # DataSource を作成または更新
            response = requests.put(data_source_url, headers=headers, json=data_source_payload)
            if response.status_code in [200, 201]:
                logger.info("✓ DataSource 'blob-documents-source' を作成しました")
            elif response.status_code == 204:
                logger.info("✓ DataSource 'blob-documents-source' は既に存在します")
            else:
                logger.error(f"❌ DataSource 作成エラー: {response.status_code} - {response.text}")
                return False
            
            logger.info("🔧 Indexer を作成中...")
            
            # Indexer 作成リクエスト
            indexer_url = f"{self.search_service_endpoint}/indexers/blob-documents-indexer?api-version={api_version}"
            indexer_payload = {
                "name": "blob-documents-indexer",
                "dataSourceName": "blob-documents-source",
                "targetIndexName": index_name,
                "schedule": {
                    "interval": "PT5M"
                },
                "parameters": {
                    "configuration": {
                        "dataToExtract": "contentAndMetadata",
                        "parsingMode": "default"
                    }
                },
                "fieldMappings": [
                    {
                        "sourceFieldName": "metadata_storage_name",
                        "targetFieldName": "filename"
                    }
                ]
            }
            
            # Indexer を作成または更新
            response = requests.put(indexer_url, headers=headers, json=indexer_payload)
            if response.status_code in [200, 201]:
                logger.info("✓ Indexer 'blob-documents-indexer' を作成しました")
            elif response.status_code == 204:
                logger.info("✓ Indexer 'blob-documents-indexer' は既に存在します")
            else:
                logger.error(f"❌ Indexer 作成エラー: {response.status_code} - {response.text}")
                return False
            
            # Indexer を即座に実行
            logger.info("🚀 Indexer を実行中...")
            run_url = f"{self.search_service_endpoint}/indexers/blob-documents-indexer/run?api-version={api_version}"
            response = requests.post(run_url, headers=headers)
            if response.status_code in [200, 202]:
                logger.info("✓ Indexer の実行を開始しました")
                logger.info("📊 インデックス化には数分かかる場合があります")
            else:
                logger.warning(f"⚠ Indexer 実行エラー: {response.status_code} - {response.text}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ DataSource/Indexer 作成エラー: {e}")
            return False
    
    def _get_subscription_id(self) -> str:
        """サブスクリプションIDを取得"""
        import os
        return os.getenv("AZURE_SUBSCRIPTION_ID", "68575d55-f60d-4d89-a32b-ad90af38faa6")
    
    def _get_resource_group(self) -> str:
        """リソースグループ名を取得"""
        import os
        return os.getenv("AZURE_RESOURCE_GROUP_NAME", "avatar-ai-staging-rg")


def setup_logging(verbose: bool = False) -> None:
    """
    ロギングを設定します
    
    Args:
        verbose: 詳細ログを有効にするかどうか
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
