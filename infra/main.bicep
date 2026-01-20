// ====================================================================================================
// AI強化リアルタイムアバターシステム - メインインフラストラクチャテンプレート
// ====================================================================================================

targetScope = 'subscription'

@minLength(3)
@maxLength(15)
@description('プロジェクトの基本名称（リソース名の接頭辞として使用）')
param projectName string = 'avatar-ai'

@description('デプロイ対象の環境名')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('リソースをデプロイするAzureリージョン')
@allowed(['japaneast', 'eastus', 'westeurope'])
param location string = 'japaneast'

@description('デプロイするフェーズ（1: 基本+AI, 2: +Search+RAG, 3: +音声入力, 4: フル機能）')
@allowed([1, 2, 3, 4])
param deploymentPhase int = 1

@description('Azure OpenAI Serviceのデプロイメント設定')
param openAIConfig object = {
  deployments: [
    {
      name: 'gpt-4.1'
      model: 'gpt-4.1'
      version: '2024-08-06'
      capacity: 30
    }
    {
      name: 'text-embedding-3-large'
      model: 'text-embedding-3-large' 
      version: '1'
      capacity: 30
    }
  ]
}

@description('タグ情報')
param tags object = {
  project: 'AI-Enhanced-Avatar-System'
  environment: environment
  costCenter: 'Innovation-Lab'
  owner: 'Development-Team'
}

// ====================================================================================================
// 変数定義
// ====================================================================================================

var resourcePrefix = '${projectName}-${environment}'
var resourceGroupName = '${resourcePrefix}-rg'

// ====================================================================================================
// リソースグループ作成
// ====================================================================================================

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ====================================================================================================
// 共通リソース（全フェーズで必要）
// ====================================================================================================

module commonResources 'modules/common.bicep' = {
  scope: resourceGroup
  params: {
    resourcePrefix: resourcePrefix
    location: location
    tags: tags
  }
}

// ====================================================================================================
// フェーズ1: 基本機能 + 生成AI（既存リソースが存在しない場合のみ）
// ====================================================================================================

module phase1Resources 'modules/phase1.bicep' = if (deploymentPhase == 1) {
  scope: resourceGroup
  params: {
    resourcePrefix: resourcePrefix
    location: location
    tags: tags
    openAIConfig: openAIConfig
    logAnalyticsWorkspaceId: commonResources.outputs.logAnalyticsWorkspaceId
  }
}

// ====================================================================================================
// フェーズ2: Azure AI Search + RAG機能（フェーズ2以上で有効）
// ====================================================================================================

module phase2Resources 'modules/phase2.bicep' = if (deploymentPhase >= 2) {
  scope: resourceGroup
  params: {
    resourcePrefix: resourcePrefix
    location: location
    tags: tags
    logAnalyticsWorkspaceId: commonResources.outputs.logAnalyticsWorkspaceId
    // Phase 1のOpenAIサービス名を参照
    existingOpenAIServiceName: '${resourcePrefix}-openai'
  }
}

// ====================================================================================================
// フェーズ3: 音声入力強化（フェーズ3以上で有効）
// ====================================================================================================

module phase3Resources 'modules/phase3.bicep' = if (deploymentPhase >= 3) {
  scope: resourceGroup
  params: {
    resourcePrefix: resourcePrefix
    location: location
    tags: tags
    logAnalyticsWorkspaceId: commonResources.outputs.logAnalyticsWorkspaceId
  }
}

// ====================================================================================================
// フェーズ4: フル機能（統合・最適化）（フェーズ4で有効）
// ====================================================================================================

module phase4Resources 'modules/phase4.bicep' = if (deploymentPhase >= 4) {
  scope: resourceGroup
  params: {
    resourcePrefix: resourcePrefix
    location: location
    tags: tags
    logAnalyticsWorkspaceId: commonResources.outputs.logAnalyticsWorkspaceId
  }
}

// ====================================================================================================
// 出力値
// ====================================================================================================

@description('作成されたリソースグループ名')
output resourceGroupName string = resourceGroup.name

@description('デプロイされたリソースのエンドポイント情報')
output endpoints object = {
  // 共通リソース
  keyVaultUri: commonResources.outputs.keyVaultUri
  
  // フェーズ1リソース（条件付き）
  speechServiceEndpoint: deploymentPhase == 1 ? phase1Resources.outputs.speechServiceEndpoint : 'https://ai-avatar-staging-speech.cognitiveservices.azure.com/'
  openAIEndpoint: deploymentPhase == 1 ? phase1Resources.outputs.openAIEndpoint : 'https://ai-avatar-staging-openai.openai.azure.com/'
  
  // フェーズ2リソース（条件付き）
  searchServiceEndpoint: deploymentPhase >= 2 ? phase2Resources!.outputs.searchServiceEndpoint : ''
  cosmosDbEndpoint: deploymentPhase >= 2 ? phase2Resources!.outputs.cosmosDbEndpoint : ''
  
  // フェーズ3以降は今後実装
}

@description('各リソースのキー・接続文字列を格納するKey Vaultのシークレット名一覧')
output keyVaultSecrets object = {
  speechServiceKey: 'speech-service-key'
  openAIApiKey: 'openai-api-key'
  searchServiceKey: deploymentPhase >= 2 ? 'search-service-key' : ''
  cosmosDbKey: deploymentPhase >= 2 ? 'cosmosdb-key' : ''
  applicationInsightsKey: 'appinsights-instrumentation-key'
}

@description('アプリケーション設定用の構成情報')
output appConfiguration object = {
  speechRegion: location
  openAIApiVersion: '2024-02-01'
  deploymentPhase: deploymentPhase
  environment: environment
  keyVaultName: commonResources.outputs.keyVaultName
}
