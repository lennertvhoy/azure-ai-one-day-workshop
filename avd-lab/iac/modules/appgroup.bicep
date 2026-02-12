// Application Group Module - Desktop Application Group for AVD

// ============== Parameters ==============
@description('Azure region for deployment')
param location string

@description('Desktop Application Group name')
param dagName string

@description('Host pool name to associate with')
param hostPoolName string

@description('Workspace name to associate with')
param workspaceName string

@description('Application group type')
param applicationGroupType string = 'Desktop'

@description('Friendly name for the application group')
param friendlyName string = 'Desktop Application Group'

@description('Description text for the application group')
param appGroupDescription string = 'Desktop Application Group for AVD Lab'

@description('Tags to apply to resources')
param tags object

// ============== Desktop Application Group ==============
resource dag 'Microsoft.DesktopVirtualization/applicationGroups@2023-09-05' = {
  name: dagName
  location: location
  properties: {
    applicationGroupType: applicationGroupType
    friendlyName: friendlyName
    description: appGroupDescription
    hostPoolArmPath: resourceId('Microsoft.DesktopVirtualization/hostPools', hostPoolName)
  }
  tags: tags
}

// ============== Workspace Association ==============
resource workspace 'Microsoft.DesktopVirtualization/workspaces@2023-09-05' existing = {
  name: workspaceName
}

resource workspaceDag 'Microsoft.DesktopVirtualization/workspaces/applicationGroups@2023-09-05' = {
  parent: workspace
  name: dagName
  properties: {
    applicationGroupPath: dag.id
  }
}

@description('Array of Entra ID object IDs for students to grant access')
param studentObjectIds array = []

// ============== RBAC Support ==============
var desktopUserRoleId = '1d18fff4-a54a-4aad-95ee-f716619069ff' // Desktop Virtualization User

resource roleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (objectId, i) in studentObjectIds: {
  scope: dag
  name: guid(dag.id, objectId, desktopUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', desktopUserRoleId)
    principalId: objectId
    principalType: 'User'
  }
}]

// ============== Outputs ==============
output dagId string = dag.id
output dagName string = dag.name
output dagType string = dag.properties.applicationGroupType
