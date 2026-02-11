targetScope = 'resourceGroup'

@description('Location for resources')
param location string = resourceGroup().location

@description('Participant/environment short name (e.g. p01, team-a).')
param participantId string

@description('Course code used for naming and tags.')
param courseCode string

@description('Owner label for tags.')
param owner string

@description('Expiry date/time in ISO-8601 for cleanup scripts.')
param expiresAt string

@description('Deploy Azure AI Search service for RAG lab.')
param deploySearch bool = true

@allowed([
  'basic'
])
param searchSku string = 'basic'

@allowed([
  'B1'
])
param appServiceSku string = 'B1'

var token = uniqueString(subscription().id, resourceGroup().name, participantId)
var planName = 'asp-${courseCode}-${participantId}'
var webAppName = take('app-${courseCode}-${participantId}-${token}', 60)
var keyVaultName = take(replace('kv${courseCode}${participantId}${token}', '-', ''), 24)
var searchName = take(replace('srch-${courseCode}-${participantId}-${token}', '_', '-'), 60)

var commonTags = {
  course: courseCode
  participant: participantId
  owner: owner
  expiresAt: expiresAt
  managedBy: 'iac-starter'
}

resource appPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  kind: 'linux'
  sku: {
    name: appServiceSku
    tier: 'Basic'
    size: appServiceSku
    capacity: 1
  }
  tags: commonTags
  properties: {
    reserved: true
  }
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      minTlsVersion: '1.2'
      ftpsState: 'FtpsOnly'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
      ]
    }
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: commonTags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    enabledForDiskEncryption: false
  }
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = if (deploySearch) {
  name: searchName
  location: location
  sku: {
    name: searchSku
  }
  tags: commonTags
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: 'free'
  }
}

resource kvRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, webApp.id, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
  }
}

output webAppName string = webApp.name
output keyVaultName string = keyVault.name
output searchServiceName string = deploySearch ? search.name : ''
output webAppPrincipalId string = webApp.identity.principalId
output resourceGroupName string = resourceGroup().name
