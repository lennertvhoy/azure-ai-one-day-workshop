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

// ============== Outputs ==============
output dagId string = dag.id
output dagName string = dag.name
output dagType string = dag.properties.applicationGroupType
