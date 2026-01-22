# Scripts ディレクトリ

このディレクトリには、**RAG インデックス作成・更新の定期バッチ処理**に関するスクリプトが含まれています。

FastAPI での実時間検索とは別に、**データの準備・インデックス化をバッチ処理として管理**します。

## 📂 ファイル構成

```
scripts/
├── README.md                       # このファイル
├── index_documents.py              # 初期インデックス作成スクリプト
├── update_search_index.py          # インデックス更新スクリプト
├── utils/
│   └── rag_indexer.py             # インデックス作成コアロジック
└── config/
    └── indexing_config.yaml        # インデックス設定ファイル
```

## 🚀 使用方法

### 1. 環境変数の設定

スクリプト実行前に、`backend/.env` に以下の環境変数を設定してください：

```bash
# Azure Search Service
AZURE_SEARCH_SERVICE_ENDPOINT=https://your-search-service.search.windows.net

# Azure Blob Storage
AZURE_STORAGE_ACCOUNT_URL=https://yourstorageaccount.blob.core.windows.net/

# Managed Identity を使用する場合は以下の設定は不要です
# (DefaultAzureCredential が自動で認証します)
USE_MANAGED_IDENTITY=true
```

### 2. 初期インデックス作成

新しいドキュメントセットからインデックスを作成します：

```bash
# 基本的な使用方法
python scripts/index_documents.py --folder ./data/documents

# カスタムコンテナ・インデックス名を指定
python scripts/index_documents.py \
  --folder ./data/documents \
  --container my-documents \
  --index-name my-custom-index

# 詳細ログを出力
python scripts/index_documents.py --folder ./data/documents --verbose
```

**出力例：**

```
============================================================
📄 ドキュメント インデックス作成スクリプト
============================================================
フォルダ: ./data/documents
コンテナ: rag-documents
インデックス: rag-index

✓ インデックス 'rag-index' が作成されました
📤 ドキュメントをアップロード中...

============================================================
📊 処理結果
============================================================
✓ アップロード成功: 42 件
❌ アップロード失敗: 0 件
⏭ スキップ: 3 件
============================================================
```

### 3. インデックス更新

既存インデックスを更新または再構築します：

```bash
# インデックスを更新（Blob Indexer が新着ドキュメント検出）
python scripts/update_search_index.py --index-name rag-index

# インデックスを再構築（削除して再作成）
python scripts/update_search_index.py --index-name rag-index --rebuild

# 新規ドキュメントをアップロードして更新
python scripts/update_search_index.py \
  --index-name rag-index \
  --folder ./data/documents \
  --container rag-documents
```

## ⏰ 定期実行設定

### cron による定期実行

毎日 午前2時にインデックスを更新するケース：

```bash
# crontab -e で編集
0 2 * * * cd /path/to/project && python scripts/update_search_index.py --index-name rag-index --verbose >> /var/log/rag-indexing.log 2>&1
```

### Azure Functions による定期実行

Azure Functions Timer Trigger で定期実行：

```python
import azure.functions as func
import subprocess

def main(mytimer: func.TimerRequest):
    result = subprocess.run(
        ["python", "scripts/update_search_index.py", "--index-name", "rag-index"],
        cwd="/mnt/azurefile/app"
    )
    return result.returncode
```

### Docker + Scheduler

Docker コンテナ内での定期実行：

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r backend/requirements.txt

# APScheduler を使用した定期実行
CMD ["python", "-c", """
import schedule
import time
from utils.rag_indexer import RAGIndexer

def update_job():
    print('Running scheduled index update...')
    # インデックス更新処理

schedule.every().day.at('02:00').do(update_job)
while True:
    schedule.run_pending()
    time.sleep(60)
"""]
```

## 🔐 認証方式

### Managed Identity（推奨）

スクリプトはデフォルトで **Managed Identity** を使用します：

```bash
# Managed Identity 認証
python scripts/index_documents.py --folder ./data/documents --use-managed-identity

# 環境変数 USE_MANAGED_IDENTITY=true の場合も同様
```

**利点：**
- API キーの管理が不要
- キーの自動ローテーション対応
- RBAC による細粒度制御
- 監査ログに記録される

### API キー認証（後方互換性）

API キーを使用する場合：

```bash
# API キーで認証
python scripts/index_documents.py \
  --folder ./data/documents \
  --search-key "your-search-key" \
  --storage-key "your-storage-key"
```

⚠ **本番環境では Managed Identity を使用してください。**

## 🔄 データフロー

```
Local Folder (data/documents/)
         ↓
    index_documents.py
         ↓
  Azure Blob Storage (rag-documents container)
         ↓
Azure AI Search (Blob Indexer or manual indexing)
         ↓
    FastAPI /api/azure-rag/search
         ↓
     Frontend (React)
```

## 📊 ログ出力

### ログレベル

- `DEBUG`: 詳細な内部動作を記録（開発時に使用）
- `INFO`: 通常の処理状況を記録（本番推奨）
- `WARNING`: 潜在的な問題を記録
- `ERROR`: エラーのみを記録

### ログ設定

```bash
# 詳細ログを有効化
python scripts/index_documents.py --folder ./data/documents --verbose

# ログファイルに出力（オプション）
python scripts/index_documents.py --folder ./data/documents 2>&1 | tee indexing.log
```

## ❌ トラブルシューティング

### エラー: "Managed Identity 認証に失敗"

```
DefaultAzureCredential failed to authenticate
```

**原因と対策：**
1. Azure CLI でログイン: `az login`
2. 環境変数が正しく設定されているか確認
3. RBAC ロール（Storage Blob Data Contributor など）が付与されているか確認

### エラー: "Search Service エンドポイントが設定されていない"

```
❌ エラー: AZURE_SEARCH_SERVICE_ENDPOINT が設定されていません
```

**対策：**
```bash
export AZURE_SEARCH_SERVICE_ENDPOINT="https://your-search-service.search.windows.net"
export AZURE_STORAGE_ACCOUNT_URL="https://yourstorageaccount.blob.core.windows.net/"

python scripts/index_documents.py --folder ./data/documents
```

### エラー: "Permission Denied"

```
Azure.Core.Exceptions.AuthenticationError: Authentication failed
```

**対策：**
- RBAC ロール確認: `az role assignment list --scope /subscriptions/YOUR_SUB_ID`
- 必要なロール:
  - `Storage Blob Data Contributor`
  - `Search Service Contributor`
  - `Search Index Data Contributor`

## 📚 参考リンク

- [Azure Search Indexer Documentation](https://learn.microsoft.com/azure/search/search-indexer-overview)
- [Azure Blob Storage Integration](https://learn.microsoft.com/azure/search/search-howto-index-json-blobs)
- [Managed Identity for Azure Resources](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/overview)

## 🛠 拡張機能の計画

- [ ] 複数フォーマット自動判別（PDF、DOCX、Excel など）
- [ ] インクリメンタルインデックス（差分更新）
- [ ] インデックス検証・ヘルスチェック
- [ ] メトリクス収集・アラート設定
- [ ] Web UI でのインデックス管理画面
