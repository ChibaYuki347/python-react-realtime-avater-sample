// ====================================================================================================
// 共通リソース - Key Vault, Application Insights, Log Analytics
// ====================================================================================================

@description('リソース名の接頭辞')
param resourcePrefix string

@description('デプロイ先のリージョン')
param location string

@description('リソースタグ')
param tags object

// ====================================================================================================
// Log Analytics Workspace（監視・ログ基盤）
// ====================================================================================================

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${resourcePrefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// ====================================================================================================
// Application Insights（アプリケーション監視）
// ====================================================================================================

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${resourcePrefix}-appinsights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ====================================================================================================
// Key Vault（機密情報管理）
// ====================================================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${resourcePrefix}-kv'
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
    enabledForDeployment: false
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// ====================================================================================================
// Key Vault診断設定
// ====================================================================================================

resource keyVaultDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'keyvault-diagnostics'
  scope: keyVault
  properties: {
    workspaceId: logAnalyticsWorkspace.id
    logs: [
      {
        category: 'AuditEvent'
        enabled: true
      }
      {
        category: 'AzurePolicyEvaluationDetails'
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

@description('Log Analytics ワークスペースのリソースID')
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id

@description('Application Insights の接続文字列')
@secure()
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString

@description('Application Insights のインストルメンテーションキー')
@secure()
output applicationInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey

@description('Key Vault の URI')
output keyVaultUri string = keyVault.properties.vaultUri

@description('Key Vault のリソース名')
output keyVaultName string = keyVault.name

@description('Key Vault のリソースID')
output keyVaultId string = keyVault.id