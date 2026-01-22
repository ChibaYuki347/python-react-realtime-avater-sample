# PythonとReactを活用したリアルタイムカスタムアバターアプリサンプル

本レポジトリではPythonとReactを使用して、リアルタイムでアバターを操作できるアプリケーションのサンプルコードを提供します。

## 構成

### 現在の構成
- **Backend (FastAPI)**: 
  - APIサーバーとしてRAG検索結果の読み込み、生成AIによるカスタムボイス・アバター生成を担当
  - Azure Speech サービスの認証トークン取得とCORS設定を実装
  - **Managed Identity** を使用したAzure リソース認証（Blob Storage, AI Search, OpenAI）
  - ローカル開発時は `backend/.env` から環境変数を読み込み

- **RAG Indexing Scripts (`scripts/`)**: 
  - ドキュメント処理・インデックス作成をバッチ処理として分離管理
  - Azure Blob Storage へのドキュメント アップロード
  - Azure AI Search インデックスの作成・更新
  - 定期実行タスク（スケジューラーと組み合わせ可能）

- **Frontend (React)**: 
  - Reactを使用してユーザーインターフェースを構築
  - Azure Speech SDKとWebRTCを使用してリアルタイムアバターを表示

- **インフラストラクチャ**:
  - Azure Blob Storage: ドキュメントリポジトリ
  - Azure AI Search: インデックス・検索エンジン
  - Azure OpenAI: 生成AI応答エンジン
  - Azure Speech Service: カスタムボイス・アバター合成

### 実装完了済み（Phase 2）
- **生成AI応答システム**: Azure OpenAI Service (GPT-4.1) を統合
- **RAG（検索拡張生成）**: Azure AI Search + Blob Storage Indexer を実装
  - Managed Identity による RBAC 認証
  - 日本語対応のセマンティック検索
- **FastAPI インテグレーション**: RAG検索 + AI応答の統合エンドポイント

## 技術詳細

### バックエンド構成（FastAPI）
**役割**: RAG インデックスの読み込み・検索、生成AI応答、カスタムボイス・アバター生成

**ファイル構成**:
```
backend/
├── main.py                         # FastAPIメインアプリケーション
├── requirements.txt                # Python依存関係管理
├── .env                            # 環境変数（本番: Key Vault経由）
├── routes/
│   ├── ai_routes.py               # AI チャット・応答エンドポイント
│   └── azure_rag_routes.py        # RAG検索・クエリ実行エンドポイント
├── services/
│   ├── azure_rag_service.py       # RAG検索・応答生成ロジック
│   └── key_vault_helper.py        # Key Vault統合（環境変数解決）
└── utils/
    └── key_vault_helper.py        # Managed Identity認証ユーティリティ
```

**主要エンドポイント**:
- `POST /api/azure-rag/query` - RAG クエリ実行（検索 + AI応答生成）
- `GET /api/azure-rag/search` - セマンティック検索
- `POST /api/azure-rag/upload-document` - ドキュメント アップロード
- `GET /api/azure-rag/health` - ヘルスチェック

### インデキシング・バッチスクリプト（`scripts/`）
**役割**: ドキュメント処理・インデックス作成を定期的なバッチ処理として実行

**ファイル構成（新規作成予定）**:
```
scripts/
├── index_documents.py             # ドキュメントのインデックス作成スクリプト
├── update_search_index.py         # 既存インデックスの更新
├── batch_process_documents.py     # バルク ドキュメント処理
├── utils/
│   └── rag_indexer.py            # インデックス作成のコア ロジック
└── config/
    └── indexing_config.yaml       # インデックス設定
```

**使用例**:
```bash
# 単一ドキュメントのインデックス作成
python scripts/index_documents.py --folder ./data/documents

# 定期実行（cron / scheduler と組み合わせ）
0 2 * * * cd /app && python scripts/update_search_index.py
```

### フロントエンド構成（React）
- `frontend/src/App.tsx`: メインReactアプリケーション
- `frontend/src/components/AvatarPlayer.tsx`: アバター表示・制御コンポーネント
- `frontend/src/utils/speechUtils.ts`: Azure Speech SDK関連ユーティリティ

### 次期開発計画（拡張機能）
- **音声入力強化**: Azure Speech-to-Text をリアルタイム統合
- **対話ループの完全自動化**: 音声入力 → RAG検索 → 生成AI応答 → アバター音声出力
- **マルチドキュメント対応**: 複数フォーマット（PDF, DOCX, TXT）の自動インデックス
- **キャッシング・最適化**: 検索結果・AI応答のキャッシング機構

## コーディングルール

### 一般ルール
- コードを変更する場合は必ず確認を得るようにします。
- 変更点はREADMEに記載し、ドキュメントを最新の状態に保ちます。
- 主要な変更点にはコメントを追加し、コードの可読性を向上させます。
- Azure関連のベストプラクティスに従い、セキュリティを重視します。

### FastAPI（バックエンド）コードスタイル
- PEP 8に準拠したコードスタイル
- 型ヒント（Type Hints）を必ず使用
- 非同期処理（async/await）を活用
- 適切な例外処理とログ出力を実装
- 環境変数を使用した設定管理
- **Managed Identity を優先**: API キーベースの認証は避け、Managed Identity（DefaultAzureCredential）を使用

### スクリプト（インデキシング）コードスタイル
- バッチ処理としても実行可能な構造
- ログ出力で実行状況を記録（--verbose オプション対応）
- エラー時の自動リトライ機構
- 処理の進捗状況をレポート（処理件数、失敗件数など）
- 定期実行対応（cron, scheduler, Azure Functions）

### React (TypeScript) コードスタイル
- 関数コンポーネントとHooksを使用
- TypeScriptでの型安全性を確保
- useEffect、useState などのHooksを適切に使用
- エラーハンドリングとユーザーフィードバックを実装

## 認証・セキュリティ要件

### Managed Identity（推奨）
- **Azure OpenAI**: Managed Identity + トークンプロバイダー
- **Azure AI Search**: Managed Identity + DefaultAzureCredential
- **Azure Blob Storage**: Managed Identity + account_url
- 利点: API キーの管理が不要、自動更新、監査ログ

### API キーベース認証（後方互換性のみ）
- Azure Speech Service: 必要に応じてキーベース認証をサポート
- 環境変数: `AZURE_*_API_KEY` で管理

### セキュリティ要件（実装済み）
- Azure Speech サービスキーはサーバーサイドでのみ使用
- 認証トークンの適切な有効期限管理
- CORS設定を適切に構成
- RBAC による Azure リソースアクセス制御

### セキュリティ要件（計画中）
- ユーザー会話履歴のプライバシー保護とデータ保持ポリシー
- 音声データの一時的な処理と適切な削除
- RAG検索時の機密情報フィルタリング
- レート制限とDoS攻撃対策の実装


## 参考情報

### ドキュメント
- `docs/realtime-synthesis-mechanism.md`: Azure Speech SDKを使用したリアルタイムアバター合成の仕組み

### アーキテクチャ
```
┌─────────────────────────────────────────────────────────────┐
│                    フロントエンド (React)                      │
│                                                             │
│  - ユーザーインターフェース                                    │
│  - リアルタイムアバター表示（Azure Speech SDK）              │
└──────────────┬──────────────────────────────────────────────┘
               │ HTTP/WebSocket
┌──────────────▼──────────────────────────────────────────────┐
│                    バックエンド (FastAPI)                      │
│                                                             │
│  ┌───────────────────────────┐   ┌──────────────────────┐ │
│  │ RAG 検索 + 応答生成        │   │ カスタムボイス・     │ │
│  │ - Blob Storage (読み込み) │   │ アバター生成         │ │
│  │ - AI Search（検索）        │   │ - Azure Speech       │ │
│  │ - OpenAI（応答生成）       │   └──────────────────────┘ │
│  └───────────────────────────┘                             │
│            ▲                                                 │
│            │ インデックスデータ                              │
└────────────┼─────────────────────────────────────────────────┘
             │
┌────────────▼──────────────────────────────────────────────┐
│          バッチスクリプト (scripts/)                        │
│                                                           │
│  - ドキュメント アップロード                               │
│  - インデックス作成・更新                                 │
│  - 定期実行（cron/scheduler）                            │
└───────────────────────────────────────────────────────────┘
             │ アップロード・インデックス化
┌────────────▼──────────────────────────────────────────────┐
│                Azure リソース                               │
│                                                           │
│  - Blob Storage（ドキュメント）                          │
│  - AI Search（インデックス）                             │
│  - OpenAI（生成AI）                                      │
│  - Speech Service（音声合成）                           │
└───────────────────────────────────────────────────────────┘
```

### 開発フロー
1. **初期セットアップ**: `scripts/index_documents.py` で data/ フォルダをインデックス化
2. **定期更新**: `scripts/update_search_index.py` を cron で定期実行
3. **FastAPI 実行**: インデックスされたデータを使って RAG クエリ処理
4. **フロントエンド**: FastAPI から RAG 結果と音声を受け取ってアバター表示