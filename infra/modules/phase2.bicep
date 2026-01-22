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

@description('Phase 1でデプロイされた既存のOpenAIサービス名')
param existingOpenAIServiceName string

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
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    semanticSearch: 'standard'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ====================================================================================================
// Azure Storage Account（RAGドキュメント保存・Blob Indexer用）
// ====================================================================================================

// Storage Account名を短縮（24文字制限対応）
var storageAccountName = length('${replace(replace(resourcePrefix, '-', ''), '_', '')}rag') > 24 
  ? '${take(replace(replace(resourcePrefix, '-', ''), '_', ''), 20)}rag'
  : '${replace(replace(resourcePrefix, '-', ''), '_', '')}rag'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    dnsEndpointType: 'Standard'
    defaultToOAuthAuthentication: false
    publicNetworkAccess: 'Enabled'
    allowCrossTenantReplication: false
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    networkAcls: {
      bypass: 'AzureServices'
      virtualNetworkRules: []
      ipRules: []
      defaultAction: 'Allow'
    }
    supportsHttpsTrafficOnly: true
    encryption: {
      requireInfrastructureEncryption: false
      services: {
        file: {
          keyType: 'Account'
          enabled: true
        }
        blob: {
          keyType: 'Account'
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    accessTier: 'Hot'
  }
}

// Blob Service の設定
resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    changeFeed: {
      enabled: false
    }
    restorePolicy: {
      enabled: false
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 7
    }
    cors: {
      corsRules: []
    }
    deleteRetentionPolicy: {
      allowPermanentDelete: false
      enabled: true
      days: 7
    }
    isVersioningEnabled: false
  }
}

// RAGドキュメント用コンテナ
resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobServices
  name: 'rag-documents'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
}

// ====================================================================================================
// RBAC: Search Service に Storage Blob Data Reader ロールを付与
// ====================================================================================================

resource searchServiceStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, searchService.id, storageAccount.id, 'Storage Blob Data Reader')
  scope: storageAccount
  properties: {
    roleDefinitionId: '/subscriptions/${subscription().subscriptionId}/providers/Microsoft.Authorization/roleDefinitions/2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
    principalId: searchService.identity.principalId
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    storageAccount
    searchService
  ]
}

// ====================================================================================================
// 注: インデックス・データソース・インデクサーは Azure Portal または Python スクリプトで作成
// ====================================================================================================

// ====================================================================================================
// Azure Cosmos DB（会話履歴・ユーザープロファイル）
// ====================================================================================================

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${resourcePrefix}-cosmosdb'
  location: 'westus3'
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: 'westus3'
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
        excludedPaths: []
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
      }
      {
        category: 'QueryRuntimeStatistics'
        enabled: true
      }
      {
        category: 'PartitionKeyStatistics'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'Requests'
        enabled: true
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

@description('Storage Account 名')
output storageAccountName string = storageAccount.name

@description('Storage Account のリソースID')
output storageAccountId string = storageAccount.id

@description('Blob Service のエンドポイント')
output blobServiceEndpoint string = storageAccount.properties.primaryEndpoints.blob

@description('ドキュメントコンテナ名')
output documentsContainerName string = documentsContainer.name

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
  'Document Storage (Azure Blob Storage)'
  'Document Indexing (Blob Indexer)'
  'Semantic Search'
  'RAG (Retrieval-Augmented Generation)'
  'Conversation History Storage'
  'User Profile Management'
  'Document Metadata Management'
  'Hybrid Search (Keyword + Semantic)'
  'Document Processing Pipeline'
]
