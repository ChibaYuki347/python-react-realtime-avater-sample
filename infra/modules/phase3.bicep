// ====================================================================================================
// フェーズ3リソース - 音声入力強化・WebSocket対応
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
// Event Hub（リアルタイム音声ストリーミング用）
// ====================================================================================================

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2024-01-01' = {
  name: '${resourcePrefix}-eventhub'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
    capacity: 1
  }
  properties: {
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    zoneRedundant: false
    isAutoInflateEnabled: true
    maximumThroughputUnits: 10
    kafkaEnabled: false
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ====================================================================================================
// Event Hub - 音声ストリーミング用
// ====================================================================================================

resource voiceStreamingHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: 'voice-streaming'
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: 1
    partitionCount: 4
    status: 'Active'
  }
}

// ====================================================================================================
// Event Hub - AI応答配信用
// ====================================================================================================

resource aiResponseHub 'Microsoft.EventHub/namespaces/eventhubs@2024-01-01' = {
  name: 'ai-response'
  parent: eventHubNamespace
  properties: {
    messageRetentionInDays: 1
    partitionCount: 2
    status: 'Active'
  }
}

// ====================================================================================================
// SignalR Service（WebSocket通信）
// ====================================================================================================

resource signalRService 'Microsoft.SignalRService/signalR@2024-03-01' = {
  name: '${resourcePrefix}-signalr'
  location: location
  tags: tags
  sku: {
    name: 'Standard_S1'
    tier: 'Standard'
    capacity: 1
  }
  kind: 'SignalR'
  properties: {
    features: [
      {
        flag: 'ServiceMode'
        value: 'Default'
      }
      {
        flag: 'EnableConnectivityLogs'
        value: 'True'
      }
      {
        flag: 'EnableMessagingLogs'
        value: 'True'
      }
      {
        flag: 'EnableLiveTrace'
        value: 'True'
      }
    ]
    cors: {
      allowedOrigins: [
        'http://localhost:3000'
        'https://*.azurestaticapps.net'
        'https://*.azurewebsites.net'
      ]
    }
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    tls: {
      clientCertEnabled: false
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ====================================================================================================
// Redis Cache（セッション管理・リアルタイムデータキャッシュ）
// ====================================================================================================

resource redisCache 'Microsoft.Cache/redis@2024-03-01' = {
  name: '${resourcePrefix}-redis'
  location: location
  tags: tags
  properties: {
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'maxmemory-reserved': '30'
      'maxfragmentationmemory-reserved': '30'
      'maxmemory-delta': '30'
    }
    redisVersion: '6.0'
    sku: {
      capacity: 1
      family: 'C'
      name: 'Standard'
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ====================================================================================================
// Key Vault参照
// ====================================================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: '${resourcePrefix}-kv'
}

// ====================================================================================================
// Key Vaultシークレット - Event Hub 接続文字列
// ====================================================================================================

resource eventHubConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'eventhub-connection-string'
  parent: keyVault
  properties: {
    value: eventHubNamespace.listKeys().value[0].primaryConnectionString
    contentType: 'Event Hub Connection String'
    attributes: {
      enabled: true
    }
  }
}

// ====================================================================================================
// Key Vaultシークレット - SignalR 接続文字列
// ====================================================================================================

resource signalRConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'signalr-connection-string'
  parent: keyVault
  properties: {
    value: 'Endpoint=https://${signalRService.name}.service.signalr.net;AccessKey=${signalRService.listKeys().primaryKey};Version=1.0;'
    contentType: 'SignalR Connection String'
    attributes: {
      enabled: true
    }
  }
}

// ====================================================================================================
// Key Vaultシークレット - Redis Cache 接続文字列
// ====================================================================================================

resource redisCacheConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'redis-connection-string'
  parent: keyVault
  properties: {
    value: '${redisCache.name}.redis.cache.windows.net:6380,password=${redisCache.listKeys().primaryKey},ssl=True,abortConnect=False'
    contentType: 'Redis Cache Connection String'
    attributes: {
      enabled: true
    }
  }
}

// ====================================================================================================
// Event Hub 診断設定
// ====================================================================================================

resource eventHubDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'eventhub-diagnostics'
  scope: eventHubNamespace
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'ArchiveLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'OperationalLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'AutoScaleLogs'
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
// SignalR Service 診断設定
// ====================================================================================================

resource signalRDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'signalr-diagnostics'
  scope: signalRService
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'AllLogs'
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
// 出力値
// ====================================================================================================

@description('Event Hub Namespace の接続エンドポイント')
output eventHubEndpoint string = eventHubNamespace.properties.serviceBusEndpoint

@description('Event Hub Namespace 名')
output eventHubNamespaceName string = eventHubNamespace.name

@description('音声ストリーミング用 Event Hub 名')
output voiceStreamingHubName string = voiceStreamingHub.name

@description('AI応答配信用 Event Hub 名')
output aiResponseHubName string = aiResponseHub.name

@description('SignalR Service のエンドポイント')
output signalREndpoint string = 'https://${signalRService.name}.service.signalr.net'

@description('SignalR Service のリソースID')
output signalRServiceId string = signalRService.id

@description('Redis Cache のホスト名')
output redisCacheHostName string = '${redisCache.name}.redis.cache.windows.net'

@description('Redis Cache のポート')
output redisCachePort int = 6380

@description('フェーズ3で利用可能な機能一覧')
output availableFeatures array = [
  'Real-time Voice Streaming'
  'WebSocket Communication'
  'Voice Input Processing'
  'Live Audio Transcription'
  'Session Management'
  'Real-time Response Distribution'
  'Audio Data Caching'
  'Multi-user Voice Handling'
]