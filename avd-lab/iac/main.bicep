// AVD Lab Environment - Main Bicep Template
// This template provisions a complete AVD lab environment for course testing

targetScope = 'subscription'

// ============== Parameters ==============
@description('Azure region for deployment')
param location string

@description('Resource group name for the AVD lab')
param resourceGroupName string

@description('Naming prefix for resources')
param namingPrefix string = 'avd'

@description('Naming suffix for resources')
param namingSuffix string = 'lab'

@description('VM size for session hosts')
param vmSize string = 'Standard_D2s_v3'

@description('VM image reference for session hosts')
param vmImage object = {
  publisher: 'MicrosoftWindowsDesktop'
  offer: 'windows-11'
  sku: 'win11-23h2-pro'
  version: 'latest'
}

@description('Host pool type: Pooled or Personal')
param hostPoolType string = 'Pooled'

@description('Load balancer type: BreadthFirst, DepthFirst, or Persistent')
param loadBalancerType string = 'BreadthFirst'

@description('Maximum sessions per host')
param maxSessionsPerHost int = 10

@description('Number of session hosts to deploy')
param numberOfSessionHosts int = 2

@description('Virtual network address prefix')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('Subnet address prefix')
param subnetAddressPrefix string = '10.0.0.0/24'

@description('AAD join type: AzureAD or ActiveDirectory')
param aadJoinType string = 'AzureAD'

@description('Domain join username (for ActiveDirectory join)')
param domainJoinUsername string = ''

@description('Domain join password (for ActiveDirectory join)')
@secure()
param domainJoinPassword string = ''

@description('Local administrator username')
param adminUsername string = 'avdadmin'

@description('Local administrator password')
@secure()
param adminPassword string

@description('Tags to apply to all resources')
param tags object = {
  'managed-by': 'avd-lab-tool'
}

@description('Expiry time for the lab environment (ISO8601)')
param expiry string = newGuid()

@description('Array of Entra ID object IDs for students to grant access')
param studentObjectIds array = []

// ============== Variables ==============
var hostPoolName = '${namingPrefix}-hp-${namingSuffix}'
var workspaceName = '${namingPrefix}-ws-${namingSuffix}'
var dagName = '${namingPrefix}-dag-${namingSuffix}'
var vnetName = '${namingPrefix}-vnet-${namingSuffix}'
var subnetName = 'default'
var nsgName = '${namingPrefix}-nsg-${namingSuffix}'

// ============== Resource Group ==============
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: union(tags, {
    'expiry': expiry
    'lab-name': namingSuffix
    'workspace-url': 'https://client.wvd.microsoft.com/arm/webclient/index.html'
  })
}

// ============== Network Module ==============
module network 'modules/network.bicep' = {
  scope: rg
  name: 'network-deployment'
  params: {
    location: location
    vnetName: vnetName
    subnetName: subnetName
    nsgName: nsgName
    vnetAddressPrefix: vnetAddressPrefix
    subnetAddressPrefix: subnetAddressPrefix
    tags: tags
  }
}

// ============== AVD Host Pool ==============
module hostPool 'modules/hostpool.bicep' = {
  scope: rg
  name: 'hostpool-deployment'
  params: {
    location: location
    hostPoolName: hostPoolName
    hostPoolType: hostPoolType
    loadBalancerType: loadBalancerType
    maxSessionsPerHost: maxSessionsPerHost
    tags: union(tags, {
      'expiry': expiry
      'lab-name': namingSuffix
    })
  }
}

// ============== AVD Workspace ==============
module workspace 'modules/workspace.bicep' = {
  scope: rg
  name: 'workspace-deployment'
  params: {
    location: location
    workspaceName: workspaceName
    tags: union(tags, {
      'expiry': expiry
      'lab-name': namingSuffix
    })
  }
}

// ============== Desktop Application Group ==============
module dag 'modules/appgroup.bicep' = {
  scope: rg
  name: 'appgroup-deployment'
  params: {
    location: location
    dagName: dagName
    hostPoolName: hostPoolName
    workspaceName: workspaceName
    tags: union(tags, {
      'expiry': expiry
      'lab-name': namingSuffix
    })
    studentObjectIds: studentObjectIds
  }
  dependsOn: [
    hostPool
    workspace
  ]
}

// ============== Session Hosts ==============
module sessionHosts 'modules/sessionhosts.bicep' = {
  scope: rg
  name: 'sessionhosts-deployment'
  params: {
    location: location
    hostPoolName: hostPoolName
    numberOfHosts: numberOfSessionHosts
    vmSize: vmSize
    vmImage: vmImage
    vnetName: vnetName
    subnetName: subnetName
    adminUsername: adminUsername
    adminPassword: adminPassword
    aadJoinType: aadJoinType
    domainJoinUsername: domainJoinUsername
    domainJoinPassword: domainJoinPassword
    namingPrefix: namingPrefix
    namingSuffix: namingSuffix
    tags: union(tags, {
      'expiry': expiry
      'lab-name': namingSuffix
    })
    studentObjectIds: studentObjectIds
  }
  dependsOn: [
    network
    hostPool
  ]
}

// ============== Outputs ==============
output resourceGroupName string = rg.name
output hostPoolName string = hostPool.outputs.hostPoolName
output workspaceName string = workspace.outputs.workspaceName
output workspaceUrl string = workspace.outputs.workspaceUrl
output dagName string = dag.outputs.dagName
output vnetName string = vnetName
output location string = location
output expiry string = expiry
