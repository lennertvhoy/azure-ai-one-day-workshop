// Workspace Module - AVD Workspace Configuration

// ============== Parameters ==============
@description('Azure region for deployment')
param location string

@description('Workspace name')
param workspaceName string

@description('Workspace friendly name')
param workspaceFriendlyName string = 'AVD Lab Workspace'

@description('Workspace description')
param workspaceDescription string = 'AVD Lab Workspace for Course Testing'

@description('Tags to apply to resources')
param tags object

// ============== Workspace ==============
resource workspace 'Microsoft.DesktopVirtualization/workspaces@2023-09-05' = {
  name: workspaceName
  location: location
  properties: {
    friendlyName: workspaceFriendlyName
    description: workspaceDescription
    publicNetworkAccess: 'Enabled'
  }
  tags: tags
}

// ============== Outputs ==============
output workspaceId string = workspace.id
output workspaceName string = workspace.name
output workspaceUrl string = 'https://client.wvd.microsoft.com/arm/webclient/index.html'
