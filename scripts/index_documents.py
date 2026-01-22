#!/usr/bin/env python3
"""
ドキュメント インデックス作成スクリプト

このスクリプトは、ローカルフォルダのドキュメントをBlob Storageにアップロードし、
Azure AI Search インデックスを作成します。定期的なバッチ処理として実行できます。

使用例:
    python index_documents.py --folder ./data/documents --container rag-documents
    python index_documents.py --folder ./data/documents --index-name my-index --verbose
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from utils.rag_indexer import RAGIndexer, setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="ドキュメント インデックス作成スクリプト"
    )
    parser.add_argument(
        "--folder",
        required=True,
        help="インデックス対象のドキュメントフォルダ",
    )
    parser.add_argument(
        "--container",
        default="rag-documents",
        help="Blob Storage コンテナ名（デフォルト: rag-documents）",
    )
    parser.add_argument(
        "--index-name",
        default="rag-index",
        help="Azure Search インデックス名（デフォルト: rag-index）",
    )
    parser.add_argument(
        "--search-endpoint",
        help="Azure Search Service エンドポイント（環境変数で設定可能）",
    )
    parser.add_argument(
        "--storage-url",
        help="Azure Blob Storage アカウント URL（環境変数で設定可能）",
    )
    parser.add_argument(
        "--use-managed-identity",
        action="store_true",
        default=True,
        help="Managed Identity を使用（デフォルト: true）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細ログを出力",
    )

    args = parser.parse_args()

    # ロギング設定
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # 環境変数から設定を読み込み
    load_dotenv()
    search_endpoint = args.search_endpoint or os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    storage_url = args.storage_url or os.getenv("AZURE_STORAGE_ACCOUNT_URL")

    if not search_endpoint:
        logger.error("❌ エラー: AZURE_SEARCH_SERVICE_ENDPOINT が設定されていません")
        sys.exit(1)

    if not storage_url:
        logger.error("❌ エラー: AZURE_STORAGE_ACCOUNT_URL が設定されていません")
        sys.exit(1)

    # フォルダの存在確認
    folder_path = Path(args.folder)
    if not folder_path.exists():
        logger.error(f"❌ エラー: フォルダが見つかりません: {args.folder}")
        sys.exit(1)

    try:
        logger.info("=" * 60)
        logger.info("📄 ドキュメント インデックス作成スクリプト")
        logger.info("=" * 60)
        logger.info(f"フォルダ: {args.folder}")
        logger.info(f"コンテナ: {args.container}")
        logger.info(f"インデックス: {args.index_name}")
        logger.info(f"Search エンドポイント: {search_endpoint}")
        logger.info(f"Storage URL: {storage_url}")
        logger.info("")

        # RAG インデクサーを初期化
        indexer = RAGIndexer(
            search_service_endpoint=search_endpoint,
            storage_account_url=storage_url,
            use_managed_identity=args.use_managed_identity,
        )

        # コンテナを作成（存在しない場合のみ）
        logger.info("📦 コンテナを確認・作成中...")
        if not indexer.create_container(args.container):
            logger.error(f"❌ コンテナ作成に失敗しました: {args.container}")
            sys.exit(1)

        # インデックスを作成
        logger.info("🔨 インデックスを作成中...")
        indexer.create_index(args.index_name)

        # ドキュメントをアップロード
        logger.info(f"📤 ドキュメントをアップロード中...")
        results = indexer.batch_upload_documents(args.container, str(folder_path))

        # 結果を出力
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 処理結果")
        logger.info("=" * 60)
        logger.info(f"✓ アップロード成功: {results['uploaded']} 件")
        logger.info(f"❌ アップロード失敗: {results['failed']} 件")
        logger.info(f"⏭ スキップ: {results['skipped']} 件")
        logger.info("=" * 60)

        if results["failed"] > 0:
            logger.warning("⚠ 一部のアップロードが失敗しました")
            sys.exit(1)

        # Indexer セットアップを自動実行
        logger.info("")
        logger.info("🔧 DataSource と Indexer を作成中...")
        
        # Storage Account 名を抽出
        storage_account_name = storage_url.split("//")[1].split(".")[0]
        
        if indexer.create_data_source_and_indexer(
            index_name=args.index_name,
            container_name=args.container,
            storage_account_name=storage_account_name
        ):
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ すべての処理が完了しました！")
            logger.info("=" * 60)
            logger.info("")
            logger.info("📊 インデックス化の進捗は Azure Portal で確認できます:")
            logger.info(f"   https://portal.azure.com")
            logger.info("")
            logger.info("💡 インデックス内容を確認:")
            logger.info(f"   curl 'https://{search_endpoint.split('//')[1]}/indexes/{args.index_name}/docs/\\$count?api-version=2024-07-01' \\")
            logger.info(f"     -H 'Authorization: Bearer $(az account get-access-token --resource https://search.azure.com --query accessToken -o tsv)'")
            logger.info("")
        else:
            logger.error("❌ DataSource/Indexer 作成に失敗しました")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
