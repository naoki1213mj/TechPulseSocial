// ========== TechPulse Social — Infrastructure ========== //
targetScope = 'resourceGroup'

@minLength(3)
@maxLength(20)
@description('A unique environment name for all resources')
param environmentName string

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Existing AI Foundry project endpoint (e.g., https://xxx.services.ai.azure.com/api/projects/xxx)')
param projectEndpoint string = ''

@description('Model deployment name')
param modelDeploymentName string = 'gpt-5.2'

@description('Image model deployment name')
param imageDeploymentName string = 'gpt-image-1.5'

@description('Vector Store ID (optional, auto-created if empty)')
param vectorStoreId string = ''

var abbrs = loadJsonContent('./abbreviations.json')
var uniqueId = toLower(uniqueString(subscription().id, environmentName, location))
var solutionPrefix = 'tp${take(uniqueId, 10)}'

// ========== Container Registry ========== //
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${abbrs.containerRegistry}${solutionPrefix}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ========== Log Analytics ========== //
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${abbrs.logAnalytics}${solutionPrefix}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ========== Container Apps Environment ========== //
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${abbrs.containerAppsEnv}${solutionPrefix}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ========== Container App ========== //
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${abbrs.containerApp}${solutionPrefix}'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'project-endpoint'
          value: projectEndpoint
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'techpulse-social'
          image: '${acr.properties.loginServer}/techpulse-social:latest'
          resources: {
            cpu: json('1.0')
            memory: '2.0Gi'
          }
          env: [
            { name: 'PROJECT_ENDPOINT', secretRef: 'project-endpoint' }
            { name: 'MODEL_DEPLOYMENT_NAME', value: modelDeploymentName }
            { name: 'IMAGE_DEPLOYMENT_NAME', value: imageDeploymentName }
            { name: 'VECTOR_STORE_ID', value: vectorStoreId }
            { name: 'SERVE_STATIC', value: 'true' }
            { name: 'HOST', value: '0.0.0.0' }
            { name: 'PORT', value: '8000' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

// ========== Outputs ========== //
output AZURE_CONTAINER_REGISTRY_NAME string = acr.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.properties.loginServer
output AZURE_CONTAINER_APP_NAME string = containerApp.name
output AZURE_CONTAINER_APP_URL string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerAppsEnv.name
