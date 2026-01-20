# インフラストラクチャ デプロイメントガイド

## 概要

このディレクトリには、AI強化リアルタイムアバターシステムのためのAzureインフラストラクチャをBicepテンプレートで定義したファイルが含まれています。

## ファイル構成

```
infra/
├── main.bicep              # メインBicepテンプレート（サブスクリプションレベル）
├── main.bicepparam         # パラメータファイル（フェーズ1開発環境用）
├── deploy.sh               # デプロイメント実行スクリプト
├── modules/
│   ├── common.bicep        # 共通リソース（Key Vault, Application Insights等）
│   ├── phase1.bicep        # フェーズ1: Speech + OpenAI Service
│   ├── phase2.bicep        # フェーズ2: AI Search + Cosmos DB (RAG機能)
│   ├── phase3.bicep        # フェーズ3: 音声入力強化（Event Hub, SignalR等）
│   └── phase4.bicep        # フェーズ4: 本番環境対応（App Service, Front Door等）
└── README.md               # このファイル
```

## フェーズ別リソース

### 🔧 共通リソース（全フェーズ）
- **Log Analytics Workspace**: 監視・ログ基盤
- **Application Insights**: アプリケーション監視
- **Key Vault**: 機密情報管理（APIキー、接続文字列）

### 🤖 フェーズ1: 生成AI応答システム
- **Azure AI Speech Service**: 音声合成・認識
- **Azure OpenAI Service**: GPT-4o + Text Embedding モデル
- **自動生成される機能**:
  - Speech-to-Text, Text-to-Speech
  - Avatar Synthesis
  - AI Chat Response
  - Conversation History

### 🔍 フェーズ2: RAG（検索拡張生成）システム  
- **Azure AI Search**: セマンティック検索・ドキュメントインデックス
- **Azure Cosmos DB**: 会話履歴・ドキュメントメタデータ保存
- **自動生成される機能**:
  - Document Indexing
  - Semantic Search
  - RAG (Retrieval-Augmented Generation)
  - User Profile Management

### 🎤 フェーズ3: 音声入力強化システム
- **Event Hub**: リアルタイム音声ストリーミング
- **SignalR Service**: WebSocket通信
- **Redis Cache**: セッション管理・データキャッシュ
- **自動生成される機能**:
  - Real-time Voice Streaming
  - Live Audio Transcription
  - Multi-user Voice Handling

### 🚀 フェーズ4: 本番環境対応
- **App Service**: 本番バックエンドホスティング
- **Static Web App**: フロントエンドホスティング
- **Front Door**: CDN・WAF保護
- **API Management**: API ゲートウェイ・レート制限
- **Container Registry**: 将来のコンテナ化対応

## クイックスタート

### 1. 前提条件

```bash
# Azure CLI のインストール・ログイン
az login

# Bicep CLI のインストール（自動で実行されますが事前確認）
az bicep install
```

### 2. フェーズ1のデプロイ（推奨）

```bash
cd infra

# 開発環境にフェーズ1をデプロイ
./deploy.sh dev 1 japaneast

# または直接 Azure CLI で実行
az deployment sub create \
  --name "avatar-ai-dev-$(date +%Y%m%d-%H%M%S)" \
  --location japaneast \
  --template-file main.bicep \
  --parameters main.bicepparam
```

### 3. 他の環境・フェーズのデプロイ

```bash
# ステージング環境にフェーズ2をデプロイ
./deploy.sh staging 2 japaneast

# 本番環境にフェーズ4をデプロイ
./deploy.sh prod 4 japaneast
```

## デプロイメントスクリプト使用方法

```bash
./deploy.sh [環境] [フェーズ] [リージョン]

# 引数:
# 環境   : dev | staging | prod (デフォルト: dev)
# フェーズ : 1 | 2 | 3 | 4 (デフォルト: 1)
# リージョン: japaneast | eastus | westeurope (デフォルト: japaneast)

# 例:
./deploy.sh dev 1           # 開発環境フェーズ1（日本東部）
./deploy.sh staging 2       # ステージング環境フェーズ2（日本東部）
./deploy.sh prod 4 eastus   # 本番環境フェーズ4（米国東部）
```

## デプロイ後の設定

### 1. 自動生成される環境設定ファイル

デプロイ完了後、`../backend/.env.{環境名}` ファイルが自動生成されます：

```bash
# 例: 開発環境の場合
../backend/.env.dev
```

### 2. Key Vault アクセス権限の設定

```bash
# あなたのユーザーアカウントにシークレット読み取り権限を付与
az keyvault set-policy \
  --name avatar-ai-dev-kv \
  --upn your-email@example.com \
  --secret-permissions get list
```

### 3. アプリケーションの起動

```bash
# バックエンド
cd ../backend
pip install -r requirements.txt
uvicorn main:app --reload

# フロントエンド  
cd ../frontend
npm install
npm start
```

## カスタマイゼーション

### パラメータの変更

`main.bicepparam` または デプロイスクリプトでパラメータを調整できます：

```bicep
param projectName = 'your-project'  // プロジェクト名
param location = 'eastus'           // リージョン変更
param openAIConfig = {              // OpenAI設定のカスタマイズ
  deployments: [
    {
      name: 'gpt-4o-mini'
      model: 'gpt-4o-mini'
      capacity: 10
    }
  ]
}
```

### リソース設定の変更

各フェーズの `modules/*.bicep` ファイルを編集してリソース設定を調整：

```bicep
// フェーズ1の例: より小さなSKUに変更
sku: {
  name: 'F0'  // Free tier（開発・テスト用）
}
```

## トラブルシューティング

### よくある問題

1. **「リソース名が既に使用されています」エラー**
   ```bash
   # projectName を変更してリトライ
   ./deploy.sh dev 1 japaneast
   ```

2. **「OpenAI サービスが利用できません」エラー**
   ```bash
   # 別のリージョンを試す
   ./deploy.sh dev 1 eastus
   ```

3. **権限エラー**
   ```bash
   # Azure サブスクリプションの所有者権限または共同作成者権限が必要
   az role assignment list --assignee $(az account show --query user.name -o tsv)
   ```

### デプロイメントの確認

```bash
# デプロイメント履歴の確認
az deployment sub list --query "[?starts_with(name, 'avatar-ai')].{Name:name, State:properties.provisioningState, Timestamp:properties.timestamp}" -o table

# リソースグループの確認
az group list --query "[?starts_with(name, 'avatar-ai')].{Name:name, Location:location, ProvisioningState:properties.provisioningState}" -o table
```

### クリーンアップ

```bash
# 開発環境のリソースグループを削除
az group delete --name avatar-ai-dev-rg --yes --no-wait

# 全てのデプロイメントを削除
az deployment sub list --query "[?starts_with(name, 'avatar-ai')].name" -o tsv | xargs -I {} az deployment sub delete --name {}
```

## コスト最適化

### 開発環境での節約設定

- **Speech Service**: F0 (Free tier) または S0 (Standard)
- **OpenAI Service**: 使用量ベースの課金、capacity を最小に
- **AI Search**: Basic tier で開始
- **Cosmos DB**: Serverless モード

### 本番環境での推奨設定

- **Speech Service**: S0 (Standard) 以上
- **OpenAI Service**: 十分な capacity を確保
- **AI Search**: Standard tier 以上
- **App Service**: P1v3 (Premium V3) 以上でスケーラビリティ確保

## 次のステップ

1. ✅ フェーズ1のインフラデプロイ完了
2. 🔄 [フェーズ1のアプリケーション実装](../docs/implementation-guide.md)
3. 🔄 フェーズ2のインフラデプロイ（RAG機能）
4. 🔄 フェーズ2のアプリケーション実装
5. 🔄 フェーズ3のインフラデプロイ（音声入力）
6. 🔄 フェーズ3のアプリケーション実装  
7. 🔄 フェーズ4の本番環境デプロイ

---

## サポート

問題がある場合は、以下を確認してください：

- [Azure Bicep ドキュメント](https://docs.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure OpenAI Service ドキュメント](https://docs.microsoft.com/azure/ai-services/openai/)
- [Azure AI Speech ドキュメント](https://docs.microsoft.com/azure/ai-services/speech-service/)
- [プロジェクトの技術アーキテクチャ](../docs/technical-architecture.md)