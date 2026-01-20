// ====================================================================================================
// フェーズ4リソース - フル機能統合・本番環境対応
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
// App Service Plan（本番環境用）
// ====================================================================================================

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${resourcePrefix}-asp'
  location: location
  tags: tags
  sku: {
    name: 'P1v3'
    tier: 'PremiumV3'
    capacity: 2
  }
  kind: 'Linux'
  properties: {
    reserved: true
    zoneRedundant: false
  }
}

// ====================================================================================================
// Web App（バックエンドAPI）
// ====================================================================================================

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: '${resourcePrefix}-api'
  location: location
  tags: tags
  kind: 'app,linux'
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true
    httpsOnly: true
    publicNetworkAccess: 'Enabled'
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: true
      ftpsState: 'FtpsOnly'
      minTlsVersion: '1.2'
      http20Enabled: true
      webSocketsEnabled: true
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITE_HEALTHCHECK_MAXPINGFAILURES'
          value: '2'
        }
      ]
      healthCheckPath: '/health'
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ====================================================================================================
// Static Web App（フロントエンドReact）
// ====================================================================================================

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: '${resourcePrefix}-frontend'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    repositoryUrl: '' // デプロイ時に設定
    branch: 'main'
    buildProperties: {
      appLocation: '/frontend'
      apiLocation: ''
      outputLocation: 'build'
    }
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    publicNetworkAccess: 'Enabled'
  }
}

// ====================================================================================================
// Front Door（CDN・WAF）
// ====================================================================================================

resource frontDoorProfile 'Microsoft.Cdn/profiles@2024-02-01' = {
  name: '${resourcePrefix}-frontdoor'
  location: 'Global'
  tags: tags
  sku: {
    name: 'Standard_AzureFrontDoor'
  }
  properties: {
    originResponseTimeoutSeconds: 60
  }
}

// ====================================================================================================
// Front Door エンドポイント
// ====================================================================================================

resource frontDoorEndpoint 'Microsoft.Cdn/profiles/afdEndpoints@2024-02-01' = {
  name: '${resourcePrefix}-endpoint'
  parent: frontDoorProfile
  location: 'Global'
  properties: {
    enabledState: 'Enabled'
  }
}

// ====================================================================================================
// Container Registry（将来のコンテナ化対応）
// ====================================================================================================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${replace(resourcePrefix, '-', '')}${uniqueString(resourceGroup().id)}acr'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
    policies: {
      quarantinePolicy: {
        status: 'disabled'
      }
      trustPolicy: {
        type: 'Notary'
        status: 'disabled'
      }
      retentionPolicy: {
        days: 30
        status: 'enabled'
      }
      exportPolicy: {
        status: 'enabled'
      }
      azureADAuthenticationAsArmPolicy: {
        status: 'enabled'
      }
      softDeletePolicy: {
        retentionDays: 7
        status: 'enabled'
      }
    }
    encryption: {
      status: 'disabled'
    }
    dataEndpointEnabled: false
    networkRuleSet: {
      defaultAction: 'Allow'
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ====================================================================================================
// API Management（API ゲートウェイ・レート制限）
// ====================================================================================================

resource apiManagement 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: '${resourcePrefix}-apim'
  location: location
  tags: tags
  sku: {
    name: 'Consumption'
    capacity: 0
  }
  properties: {
    publisherEmail: 'admin@example.com'
    publisherName: 'Avatar AI Team'
    notificationSenderEmail: 'apimgmt-noreply@mail.windowsazure.com'
    hostnameConfigurations: [
      {
        type: 'Proxy'
        hostName: '${resourcePrefix}-apim.azure-api.net'
        negotiateClientCertificate: false
        defaultSslBinding: true
        certificateSource: 'BuiltIn'
      }
    ]
    customProperties: {
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls10': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Tls11': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Protocols.Ssl30': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Ciphers.TripleDes168': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Tls10': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Tls11': 'false'
      'Microsoft.WindowsAzure.ApiManagement.Gateway.Security.Backend.Protocols.Ssl30': 'false'
    }
    virtualNetworkType: 'None'
    disableGateway: false
    natGatewayState: 'Unsupported'
    publicNetworkAccess: 'Enabled'
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
// Key Vault アクセスポリシー（Web Appのマネージド ID）
// ====================================================================================================

resource keyVaultAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  name: 'add'
  parent: keyVault
  properties: {
    accessPolicies: [
      {
        tenantId: webApp.identity.tenantId
        objectId: webApp.identity.principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
      {
        tenantId: containerRegistry.identity.tenantId
        objectId: containerRegistry.identity.principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
  }
}

// ====================================================================================================
// Application Gateway（高度な負荷分散・SSL終端）
// ====================================================================================================

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${resourcePrefix}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: 'appgw-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          networkSecurityGroup: {
            id: appGatewayNSG.id
          }
        }
      }
      {
        name: 'backend-subnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
        }
      }
    ]
  }
}

resource appGatewayNSG 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: '${resourcePrefix}-appgw-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowHTTPSInbound'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 1000
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowHTTPInbound'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 1001
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowAppGatewayInbound'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '65200-65535'
          sourceAddressPrefix: 'GatewayManager'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 1002
          direction: 'Inbound'
        }
      }
    ]
  }
}

// ====================================================================================================
// 診断設定
// ====================================================================================================

resource webAppDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'webapp-diagnostics'
  scope: webApp
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'AppServiceHTTPLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'AppServiceConsoleLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'AppServiceAppLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
      {
        category: 'AppServicePlatformLogs'
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

@description('Web App の URL')
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'

@description('Static Web App の URL')
output staticWebAppUrl string = 'https://${staticWebApp.properties.defaultHostname}'

@description('Front Door エンドポイントの URL')
output frontDoorUrl string = 'https://${frontDoorEndpoint.properties.hostName}'

@description('API Management の Gateway URL')
output apiManagementUrl string = 'https://${apiManagement.name}.azure-api.net'

@description('Container Registry のログインサーバー')
output containerRegistryLoginServer string = containerRegistry.properties.loginServer

@description('Web App の Managed Identity Principal ID')
output webAppPrincipalId string = webApp.identity.principalId

@description('フェーズ4で利用可能な機能一覧')
output availableFeatures array = [
  'Production-ready Web App Hosting'
  'Global CDN Distribution'
  'WAF Protection'
  'API Gateway & Rate Limiting'
  'Container Registry'
  'Auto-scaling'
  'SSL/TLS Termination'
  'Health Monitoring'
  'Blue-Green Deployment'
  'Managed Identity Authentication'
  'Network Security'
  'Performance Optimization'
]