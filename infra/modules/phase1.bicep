// ====================================================================================================
// フェーズ1リソース - Speech Service + Azure OpenAI Service
// ====================================================================================================

@description('リソース名の接頭辞')
param resourcePrefix string

@description('デプロイ先のリージョン')
param location string

@description('リソースタグ')
param tags object

@description('Azure OpenAI Serviceの設定')
param openAIConfig object

@description('Log Analytics ワークスペースのリソースID')
param logAnalyticsWorkspaceId string

// ====================================================================================================
// Azure AI Speech Service（既存サービスの強化）
// ====================================================================================================

resource speechService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-speech'
  location: location
  tags: tags
  kind: 'SpeechServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${resourcePrefix}-speech'
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
    disableLocalAuth: false
  }
}

// ====================================================================================================
// Azure OpenAI Service（生成AI機能）
// ====================================================================================================

resource openAIService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: '${resourcePrefix}-openai'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${resourcePrefix}-openai'
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
    disableLocalAuth: false
  }
}

// ====================================================================================================
// Azure OpenAI デプロイメント（GPT-4.1）
// ====================================================================================================

resource gpt41Deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  name: openAIConfig.deployments[0].name
  parent: openAIService
  properties: {
    model: {
      format: 'OpenAI'
      name: openAIConfig.deployments[0].model
      version: openAIConfig.deployments[0].version
    }
    raiPolicyName: 'Microsoft.Default'
  }
  sku: {
    name: 'Standard'
    capacity: openAIConfig.deployments[0].capacity
  }
}

// ====================================================================================================
// Azure OpenAI デプロイメント（Text Embedding）
// ====================================================================================================

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  name: openAIConfig.deployments[1].name
  parent: openAIService
  dependsOn: [gpt41Deployment] // 順次デプロイ
  properties: {
    model: {
      format: 'OpenAI'
      name: openAIConfig.deployments[1].model
      version: openAIConfig.deployments[1].version
    }
    raiPolicyName: 'Microsoft.Default'
  }
  sku: {
    name: 'Standard'
    capacity: openAIConfig.deployments[1].capacity
  }
}

// ====================================================================================================
// Key Vault参照（シークレット格納用）
// ====================================================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: '${resourcePrefix}-kv'
}

// ====================================================================================================
// Key Vaultシークレット - Speech Service Key
// ====================================================================================================

resource speechServiceKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'speech-service-key'
  parent: keyVault
  properties: {
    value: speechService.listKeys().key1
    contentType: 'Azure Speech Service Key'
    attributes: {
      enabled: true
    }
  }
}

// ====================================================================================================
// Key Vaultシークレット - OpenAI API Key
// ====================================================================================================

resource openAIKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'openai-api-key'
  parent: keyVault
  properties: {
    value: openAIService.listKeys().key1
    contentType: 'Azure OpenAI Service Key'
    attributes: {
      enabled: true
    }
  }
}

// ====================================================================================================
// Speech Service 診断設定
// ====================================================================================================

resource speechServiceDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'speech-diagnostics'
  scope: speechService
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'Audit'
        enabled: true
      }
      {
        category: 'RequestResponse'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// ====================================================================================================
// OpenAI Service 診断設定
// ====================================================================================================

resource openAIDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'openai-diagnostics'
  scope: openAIService
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'Audit'
        enabled: true
      }
      {
        category: 'RequestResponse'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

// ====================================================================================================
// 出力値
// ====================================================================================================

@description('Speech Service のエンドポイント')
output speechServiceEndpoint string = speechService.properties.endpoint

@description('Speech Service のリージョン')
output speechServiceRegion string = speechService.location

@description('Speech Service のリソースID')
output speechServiceId string = speechService.id

@description('Azure OpenAI Service のエンドポイント')
output openAIEndpoint string = openAIService.properties.endpoint

@description('Azure OpenAI Service のリソースID')
output openAIServiceId string = openAIService.id

@description('GPT-4.1 デプロイメント名')
output gpt4oDeploymentName string = gpt41Deployment.name

@description('Embedding デプロイメント名')
output embeddingDeploymentName string = embeddingDeployment.name

@description('フェーズ1で利用可能な機能一覧')
output availableFeatures array = [
  'Speech-to-Text'
  'Text-to-Speech'
  'Avatar Synthesis'
  'AI Chat Response'
  'Conversation History'
]