// ====================================================================================================
// フェーズ2リソース - Azure AI Search + Cosmos DB（RAG機能）
// ====================================================================================================

@description('リソース名の接頭辞')
param resourcePrefix string

@description('デプロイ先のリージョン')
param location string

@description('リソースタグ')
param tags object

@description('Log Analytics ワークスペースのリソースID')
param logAnalyticsWorkspaceId string

// ====================================================================================================
// Azure AI Search Service（セマンティック検索・RAG機能）
// ====================================================================================================

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: '${resourcePrefix}-search'
  location: location
  tags: tags
  sku: {
    name: 'standard'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    networkRuleSet: {
      ipRules: []
      bypass: 'AzureServices'
    }
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
    disableLocalAuth: false
    authOptions: {
      apiKeyOnly: {}
    }
    semanticSearch: 'standard'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ====================================================================================================
// Azure Cosmos DB（会話履歴・ユーザープロファイル）
// ====================================================================================================

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${resourcePrefix}-cosmosdb'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    publicNetworkAccess: 'Enabled'
    networkAclBypass: 'AzureServices'
    networkAclBypassResourceIds: []
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 168
        backupStorageRedundancy: 'Local'
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ====================================================================================================
// Cosmos DB データベース
// ====================================================================================================

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  name: 'avatar_conversations'
  parent: cosmosDbAccount
  properties: {
    resource: {
      id: 'avatar_conversations'
    }
  }
}

// ====================================================================================================
// Cosmos DB コンテナ - 会話セッション
// ====================================================================================================

resource conversationContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  name: 'conversation_sessions'
  parent: cosmosDatabase
  properties: {
    resource: {
      id: 'conversation_sessions'
      partitionKey: {
        paths: ['/userId']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/messages/*/audioData/?'
          }
        ]
      }
      uniqueKeyPolicy: {
        uniqueKeys: []
      }
    }
  }
}

// ====================================================================================================
// Cosmos DB コンテナ - ドキュメントメタデータ
// ====================================================================================================

resource documentContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  name: 'document_metadata'
  parent: cosmosDatabase
  properties: {
    resource: {
      id: 'document_metadata'
      partitionKey: {
        paths: ['/category']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          {
            path: '/*'
          }
        ]
      }
    }
  }
}

// ====================================================================================================
// Key Vault参照
// ====================================================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: '${resourcePrefix}-kv'
}

// ====================================================================================================
// Key Vaultシークレット - Search Service Key
// ====================================================================================================

resource searchServiceKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'search-service-key'
  parent: keyVault
  properties: {
    value: searchService.listAdminKeys().primaryKey
    contentType: 'Azure AI Search Service Admin Key'
    attributes: {
      enabled: true
    }
  }
}

// ====================================================================================================
// Key Vaultシークレット - Cosmos DB Key
// ====================================================================================================

resource cosmosDbKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'cosmosdb-key'
  parent: keyVault
  properties: {
    value: cosmosDbAccount.listKeys().primaryMasterKey
    contentType: 'Azure Cosmos DB Primary Key'
    attributes: {
      enabled: true
    }
  }
}

// ====================================================================================================
// Key Vaultシークレット - Cosmos DB 接続文字列
// ====================================================================================================

resource cosmosDbConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'cosmosdb-connection-string'
  parent: keyVault
  properties: {
    value: 'AccountEndpoint=${cosmosDbAccount.properties.documentEndpoint};AccountKey=${cosmosDbAccount.listKeys().primaryMasterKey};'
    contentType: 'Azure Cosmos DB Connection String'
    attributes: {
      enabled: true
    }
  }
}

// ====================================================================================================
// Search Service 診断設定
// ====================================================================================================

resource searchServiceDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'search-diagnostics'
  scope: searchService
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'OperationLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
  }
}

// ====================================================================================================
// Cosmos DB 診断設定
// ====================================================================================================

resource cosmosDbDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'cosmosdb-diagnostics'
  scope: cosmosDbAccount
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'DataPlaneRequests'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'QueryRuntimeStatistics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'PartitionKeyStatistics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
    metrics: [
      {
        category: 'Requests'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
  }
}

// ====================================================================================================
// 出力値
// ====================================================================================================

@description('Azure AI Search Service のエンドポイント')
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net'

@description('Azure AI Search Service のリソースID')
output searchServiceId string = searchService.id

@description('Azure AI Search Service 名')
output searchServiceName string = searchService.name

@description('Azure Cosmos DB のエンドポイント')
output cosmosDbEndpoint string = cosmosDbAccount.properties.documentEndpoint

@description('Azure Cosmos DB のリソースID')
output cosmosDbId string = cosmosDbAccount.id

@description('Azure Cosmos DB アカウント名')
output cosmosDbAccountName string = cosmosDbAccount.name

@description('Cosmos DB データベース名')
output cosmosDatabaseName string = cosmosDatabase.name

@description('フェーズ2で利用可能な機能一覧')
output availableFeatures array = [
  'Document Indexing'
  'Semantic Search'
  'RAG (Retrieval-Augmented Generation)'
  'Conversation History Storage'
  'User Profile Management'
  'Document Metadata Management'
  'Hybrid Search (Keyword + Semantic)'
]