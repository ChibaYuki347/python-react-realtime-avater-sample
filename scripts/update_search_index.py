#!/usr/bin/env python3
"""
検索インデックス更新スクリプト

このスクリプトは、既存のAzure AI Searchインデックスを更新または再構築します。
定期的なバッチ処理としてcronやAzure Functionsから実行できます。

使用例:
    python update_search_index.py --index-name my-index
    python update_search_index.py --index-name my-index --container rag-documents --folder ./data/documents
    python update_search_index.py --index-name my-index --rebuild --verbose
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
        description="Azure AI Search インデックス更新スクリプト"
    )
    parser.add_argument(
        "--index-name",
        default="rag-index",
        help="更新対象のインデックス名（デフォルト: rag-index）",
    )
    parser.add_argument(
        "--container",
        default="rag-documents",
        help="Blob Storage コンテナ名（デフォルト: rag-documents）",
    )
    parser.add_argument(
        "--folder",
        help="更新対象のドキュメントフォルダ",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="インデックスを再構築（削除して再作成）",
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

    try:
        logger.info("=" * 60)
        logger.info("🔄 検索インデックス更新スクリプト")
        logger.info("=" * 60)
        logger.info(f"インデックス: {args.index_name}")
        logger.info(f"コンテナ: {args.container}")
        logger.info(f"Rebuild: {'有効' if args.rebuild else '無効'}")
        if args.folder:
            logger.info(f"フォルダ: {args.folder}")
        logger.info("")

        # RAG インデクサーを初期化
        indexer = RAGIndexer(
            search_service_endpoint=search_endpoint,
            storage_account_url=storage_url,
            use_managed_identity=args.use_managed_identity,
        )

        # コンテナを作成（存在しない場合のみ）
        if args.folder:
            logger.info("📦 コンテナを確認・作成中...")
            if not indexer.create_container(args.container):
                logger.error(f"❌ コンテナ作成に失敗しました: {args.container}")
                sys.exit(1)

        # インデックスを作成または再構築
        if args.rebuild:
            logger.info("🔨 インデックスを再構築中...")
            # 注：削除機能は SearchIndexClient.delete_index() を使用
            try:
                indexer.search_index_client.delete_index(args.index_name)
                logger.info(f"✓ 既存インデックス '{args.index_name}' を削除しました")
            except Exception as e:
                logger.warning(f"⚠ インデックス削除エラー（存在しない可能性あり）: {e}")
        else:
            logger.info("🔍 インデックスを確認中...")

        # 新しいインデックスを作成
        indexer.create_index(args.index_name)

        # フォルダが指定されている場合はドキュメントをアップロード
        if args.folder:
            folder_path = Path(args.folder)
            if not folder_path.exists():
                logger.error(f"❌ エラー: フォルダが見つかりません: {args.folder}")
                sys.exit(1)

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
        else:
            logger.info("✓ インデックスの更新が完了しました")

    except Exception as e:
        logger.error(f"❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
