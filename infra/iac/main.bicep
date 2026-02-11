targetScope = 'subscription'

@description('Location for the participant resource group and resources.')
param location string = 'westeurope'

@description('Participant/environment short name (e.g. p01, team-a).')
@minLength(2)
param participantId string

@description('Course code used for tagging and naming.')
param courseCode string = 'azure-ai-1day'

@description('Owner label for tags (trainer or participant email/alias).')
param owner string = 'trainer'

@description('Expiry date/time in ISO-8601 (used by cleanup scripts).')
param expiresAt string = '2099-12-31T23:59:59Z'

@description('Deploy Azure AI Search service for RAG lab.')
param deploySearch bool = true

@description('Azure AI Search sku. Keep basic for training cost control.')
@allowed([
  'basic'
])
param searchSku string = 'basic'

@description('App Service plan SKU for training web app.')
@allowed([
  'B1'
])
param appServiceSku string = 'B1'

var safeParticipant = toLower(replace(replace(participantId, '_', '-'), ' ', '-'))
var rgName = 'rg-${courseCode}-${safeParticipant}'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: {
    course: courseCode
    participant: safeParticipant
    owner: owner
    expiresAt: expiresAt
    managedBy: 'iac-starter'
  }
}

module participantEnv './participant-env.bicep' = {
  name: 'participant-env-${safeParticipant}'
  scope: rg
  params: {
    location: location
    participantId: safeParticipant
    courseCode: courseCode
    owner: owner
    expiresAt: expiresAt
    deploySearch: deploySearch
    searchSku: searchSku
    appServiceSku: appServiceSku
  }
}

output resourceGroupName string = rg.name
output webAppName string = participantEnv.outputs.webAppName
output keyVaultName string = participantEnv.outputs.keyVaultName
output searchServiceName string = participantEnv.outputs.searchServiceName
