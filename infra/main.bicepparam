using './main.bicep'

// ====================================================================================================
// フェーズ1開発環境 - パラメータ設定
// ====================================================================================================

param projectName = 'ai-avatar'
param environment = 'staging'
param location = 'eastus'
param deploymentPhase = 1

param openAIConfig = {
  deployments: [
    {
      name: 'gpt-4-1'
      model: 'gpt-4.1'
      version: '2025-04-14'
      capacity: 10
    }
    {
      name: 'text-embedding-3-large'
      model: 'text-embedding-3-large'
      version: '1'
      capacity: 10
    }
  ]
}

param tags = {
  project: 'AI-Enhanced-Avatar-System'
  environment: 'dev'
  phase: 'phase1'
  costCenter: 'Innovation-Lab'
  owner: 'Development-Team'
  createdBy: 'bicep-template'
  purpose: 'ai-avatar-development'
}