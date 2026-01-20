#!/bin/bash

# ====================================================================================================
# AI強化リアルタイムアバターシステム - インフラストラクチャデプロイスクリプト
# ====================================================================================================

set -e

# 色付きログ用の定数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ====================================================================================================
# 設定変数
# ====================================================================================================

PROJECT_NAME="avatar-ai"
ENVIRONMENT=${1:-"dev"}  # 第一引数で環境指定、デフォルトはdev
DEPLOYMENT_PHASE=${2:-1}  # 第二引数でフェーズ指定、デフォルトは1
LOCATION=${3:-"japaneast"}  # 第三引数でリージョン指定、デフォルトは日本東部
SUBSCRIPTION_ID=""  # Azure CLIで設定されたサブスクリプションを使用

# ====================================================================================================
# 引数チェック
# ====================================================================================================

if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    log_error "無効な環境名です。dev, staging, prod のいずれかを指定してください。"
    exit 1
fi

if [[ ! "$DEPLOYMENT_PHASE" =~ ^[1-4]$ ]]; then
    log_error "無効なフェーズです。1-4 のいずれかを指定してください。"
    exit 1
fi

log_info "=========================================="
log_info "AI強化リアルタイムアバターシステム デプロイ開始"
log_info "=========================================="
log_info "プロジェクト名: $PROJECT_NAME"
log_info "環境: $ENVIRONMENT"
log_info "フェーズ: $DEPLOYMENT_PHASE"
log_info "リージョン: $LOCATION"
log_info "=========================================="

# ====================================================================================================
# 前提条件チェック
# ====================================================================================================

log_info "前提条件をチェックしています..."

# Azure CLI チェック
if ! command -v az &> /dev/null; then
    log_error "Azure CLI が見つかりません。インストールしてください。"
    exit 1
fi

# Azure CLI ログインチェック
if ! az account show &> /dev/null; then
    log_error "Azure CLI にログインしていません。'az login' を実行してください。"
    exit 1
fi

# Bicep CLI チェック
if ! az bicep version &> /dev/null; then
    log_info "Bicep CLI をインストールしています..."
    az bicep install
fi

log_success "前提条件チェック完了"

# ====================================================================================================
# サブスクリプション情報取得
# ====================================================================================================

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

log_info "使用するサブスクリプション:"
log_info "  ID: $SUBSCRIPTION_ID"
log_info "  名前: $SUBSCRIPTION_NAME"

# ====================================================================================================
# デプロイメント実行
# ====================================================================================================

log_info "フェーズ$DEPLOYMENT_PHASE のインフラストラクチャをデプロイしています..."

DEPLOYMENT_NAME="${PROJECT_NAME}-${ENVIRONMENT}-phase${DEPLOYMENT_PHASE}-$(date +%Y%m%d-%H%M%S)"

# Bicep デプロイメント実行
log_info "Bicepテンプレートをデプロイしています..."

# パラメータを直接指定してデプロイ
DEPLOYMENT_OUTPUT=$(az deployment sub create \
  --name "$DEPLOYMENT_NAME" \
  --location "$LOCATION" \
  --template-file "main.bicep" \
  --parameters projectName="$PROJECT_NAME" \
               environment="$ENVIRONMENT" \
               location="$LOCATION" \
               deploymentPhase=$DEPLOYMENT_PHASE \
               openAIConfig='{
                 "deployments": [
                   {
                     "name": "gpt-4-1",
                     "model": "gpt-4.1",
                     "version": "2025-04-14",
                     "capacity": 10
                   },
                   {
                     "name": "text-embedding-3-large",
                     "model": "text-embedding-3-large",
                     "version": "1",
                     "capacity": 10
                   }
                 ]
               }' \
               tags='{
                 "project": "AI-Enhanced-Avatar-System",
                 "environment": "'$ENVIRONMENT'",
                 "phase": "phase'$DEPLOYMENT_PHASE'",
                 "costCenter": "Innovation-Lab",
                 "owner": "Development-Team",
                 "createdBy": "deploy-script",
                 "purpose": "ai-avatar-development"
               }' \
  --output json)

# 一時ファイル削除は不要

if [ $? -eq 0 ]; then
    log_success "デプロイメント完了!"
    
    # デプロイメント結果の解析
    if command -v jq &> /dev/null; then
        RESOURCE_GROUP_NAME=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.resourceGroupName.value')
        ENDPOINTS=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.endpoints.value')
        KEY_VAULT_SECRETS=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.keyVaultSecrets.value')
        APP_CONFIG=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.appConfiguration.value')
    else
        log_warning "jqがインストールされていません。詳細情報の表示をスキップします。"
        RESOURCE_GROUP_NAME="${PROJECT_NAME}-${ENVIRONMENT}-rg"
        ENDPOINTS=""
        KEY_VAULT_SECRETS=""
        APP_CONFIG=""
    fi
    
    log_info "=========================================="
    log_info "デプロイメント結果"
    log_info "=========================================="
    log_info "リソースグループ: $RESOURCE_GROUP_NAME"
    log_info "デプロイメント名: $DEPLOYMENT_NAME"
    
    if [ -n "$ENDPOINTS" ] && [ "$ENDPOINTS" != "null" ]; then
        echo
        log_info "エンドポイント情報:"
        echo "$ENDPOINTS" | jq '.'
        echo
        log_info "Key Vault シークレット名:"
        echo "$KEY_VAULT_SECRETS" | jq '.'
        echo
        log_info "アプリケーション設定:"
        echo "$APP_CONFIG" | jq '.'
    fi
    
else
    log_error "デプロイメント失敗!"
    exit 1
fi

# ====================================================================================================
# 環境設定ファイル生成
# ====================================================================================================

log_info "環境設定ファイルを生成しています..."

ENV_FILE="../backend/.env.${ENVIRONMENT}"
cat > "$ENV_FILE" << EOF
# ====================================================================================================
# AI強化リアルタイムアバターシステム - 環境設定
# 自動生成日時: $(date)
# 環境: $ENVIRONMENT
# フェーズ: $DEPLOYMENT_PHASE
# ====================================================================================================

# Azure基本設定
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP_NAME=$RESOURCE_GROUP_NAME
AZURE_LOCATION=$LOCATION

# Key Vault設定
AZURE_KEY_VAULT_NAME=${PROJECT_NAME}-${ENVIRONMENT}-kv

# Speech Service設定
SPEECH_KEY=\${KEY_VAULT_SECRET:speech-service-key}
SPEECH_REGION=$LOCATION

# Azure OpenAI設定
AZURE_OPENAI_API_KEY=\${KEY_VAULT_SECRET:openai-api-key}
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-02-01

# Application Insights設定
APPLICATIONINSIGHTS_CONNECTION_STRING=\${KEY_VAULT_SECRET:appinsights-connection-string}

EOF

# フェーズ2以降の設定を追加
if [ "$DEPLOYMENT_PHASE" -ge 2 ]; then
    cat >> "$ENV_FILE" << EOF
# Azure AI Search設定（フェーズ2+）
AZURE_SEARCH_SERVICE_ENDPOINT=$(echo "$ENDPOINTS" | jq -r '.searchServiceEndpoint')
AZURE_SEARCH_API_KEY=\${KEY_VAULT_SECRET:search-service-key}
AZURE_SEARCH_INDEX_NAME=documents-index

# Cosmos DB設定（フェーズ2+）
COSMOS_DB_ENDPOINT=$(echo "$ENDPOINTS" | jq -r '.cosmosDbEndpoint')
COSMOS_DB_KEY=\${KEY_VAULT_SECRET:cosmosdb-key}
COSMOS_DB_DATABASE_NAME=avatar_conversations

EOF
fi

log_success "環境設定ファイル作成完了: $ENV_FILE"

# ====================================================================================================
# 次のステップ案内
# ====================================================================================================

log_info "=========================================="
log_info "次のステップ"
log_info "=========================================="
log_info "1. 環境設定ファイルを確認してください:"
log_info "   cat $ENV_FILE"
echo
log_info "2. バックエンドの依存関係をインストールしてください:"
log_info "   cd ../backend && pip install -r requirements.txt"
echo
log_info "3. フロントエンドの依存関係をインストールしてください:"
log_info "   cd ../frontend && npm install"
echo
log_info "4. Key Vaultからシークレットを取得するためのアクセス権限を設定してください:"
log_info "   az keyvault set-policy --name ${PROJECT_NAME}-${ENVIRONMENT}-kv --upn <your-email> --secret-permissions get list"
echo
log_info "5. アプリケーションを起動してテストしてください:"
log_info "   cd ../backend && uvicorn main:app --reload"
log_info "   cd ../frontend && npm start"
echo
log_success "フェーズ$DEPLOYMENT_PHASE のインフラストラクチャデプロイが完了しました! 🎉"