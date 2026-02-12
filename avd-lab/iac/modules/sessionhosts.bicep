// Session Hosts Module - VMs for AVD Session Hosts

// ============== Parameters ==============
@description('Azure region for deployment')
param location string

@description('Host pool name to register session hosts with')
param hostPoolName string

@description('Number of session hosts to deploy')
@minValue(1)
@maxValue(100)
param numberOfHosts int = 2

@description('VM size for session hosts')
param vmSize string = 'Standard_D2s_v3'

@description('VM image reference')
param vmImage object

@description('Virtual network name')
param vnetName string

@description('Subnet name')
param subnetName string

@description('Local administrator username')
param adminUsername string

@description('Local administrator password')
@secure()
param adminPassword string

@description('AAD join type: AzureAD or ActiveDirectory')
@allowed([
  'AzureAD'
  'ActiveDirectory'
])
param aadJoinType string = 'AzureAD'

@description('Domain join username (for ActiveDirectory)')
param domainJoinUsername string = ''

@description('Domain join password (for ActiveDirectory)')
@secure()
param domainJoinPassword string = ''

@description('Naming prefix for VMs')
param namingPrefix string

@description('Naming suffix for VMs')
param namingSuffix string

@description('Tags to apply to resources')
param tags object

// ============== Variables ==============
var vmNames = [for i in range(0, numberOfHosts): '${namingPrefix}-vm-${namingSuffix}-${padLeft(string(i + 1), 2, '0')}']
var nicNames = [for i in range(0, numberOfHosts): '${namingPrefix}-nic-${namingSuffix}-${padLeft(string(i + 1), 2, '0')}']
var diskNames = [for i in range(0, numberOfHosts): '${namingPrefix}-disk-${namingSuffix}-${padLeft(string(i + 1), 2, '0')}']

// ============== Get Host Pool Registration Token ==============
resource hostPool 'Microsoft.DesktopVirtualization/hostPools@2023-09-05' existing = {
  name: hostPoolName
}

// ============== Network Interfaces ==============
resource nics 'Microsoft.Network/networkInterfaces@2023-04-01' = [for i in range(0, numberOfHosts): {
  name: nicNames[i]
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: {
            id: resourceId('Microsoft.Network/virtualNetworks/subnets', vnetName, subnetName)
          }
        }
      }
    ]
    enableAcceleratedNetworking: true
  }
  tags: tags
}]

// ============== Virtual Machines ==============
resource vms 'Microsoft.Compute/virtualMachines@2023-03-01' = [for i in range(0, numberOfHosts): {
  name: vmNames[i]
  location: location
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    osProfile: {
      computerName: vmNames[i]
      adminUsername: adminUsername
      adminPassword: adminPassword
      windowsConfiguration: {
        enableAutomaticUpdates: true
        provisionVMAgent: true
        timeZone: 'UTC'
      }
    }
    storageProfile: {
      imageReference: vmImage
      osDisk: {
        name: diskNames[i]
        caching: 'ReadWrite'
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'Premium_LRS'
        }
        diskSizeGB: 127
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nics[i].id
          properties: {
            primary: true
          }
        }
      ]
    }
    licenseType: 'Windows_Client'
  }
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
}]

// ============== VM Extensions ==============
// Azure AD Join Extension
resource aadJoinExtension 'Microsoft.Compute/virtualMachines/extensions@2023-03-01' = [for i in range(0, numberOfHosts): if (aadJoinType == 'AzureAD') {
  name: '${vmNames[i]}/AADLoginForWindows'
  location: location
  properties: {
    publisher: 'Microsoft.Azure.ActiveDirectory'
    type: 'AADLoginForWindows'
    typeHandlerVersion: '2.0'
    autoUpgradeMinorVersion: true
    settings: {
      mdmId: '0000000a-0000-0000-c000-000000000000'
    }
  }
  dependsOn: [
    vms
  ]
}]

// AVD Agent Extension
resource avdAgentExtension 'Microsoft.Compute/virtualMachines/extensions@2023-03-01' = [for i in range(0, numberOfHosts): {
  name: '${vmNames[i]}/AVDAgent'
  location: location
  properties: {
    publisher: 'Microsoft.DesktopVirtualization'
    type: 'AVDAgent'
    typeHandlerVersion: '1.0'
    autoUpgradeMinorVersion: true
    settings: {
      HostPoolName: hostPoolName
      RegistrationToken: hostPool.properties.registrationInfo.token
    }
  }
  dependsOn: [
    vms
    aadJoinExtension
  ]
}]

// AVD Geneva Monitoring Extension
resource avdMonitoringExtension 'Microsoft.Compute/virtualMachines/extensions@2023-03-01' = [for i in range(0, numberOfHosts): {
  name: '${vmNames[i]}/AVDMonitoring'
  location: location
  properties: {
    publisher: 'Microsoft.DesktopVirtualization'
    type: 'AVDMonitoring'
    typeHandlerVersion: '1.0'
    autoUpgradeMinorVersion: true
    settings: {}
  }
  dependsOn: [
    vms
    avdAgentExtension
  ]
}]

// ============== Outputs ==============
output vmNames array = vmNames
output vmIds array = map(vms, vm => vm.id)
output numberOfHosts int = numberOfHosts
