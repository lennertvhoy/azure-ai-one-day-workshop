// Network Module - VNet, Subnet, and NSG for AVD Session Hosts

// ============== Parameters ==============
@description('Azure region for deployment')
param location string

@description('Virtual network name')
param vnetName string

@description('Subnet name')
param subnetName string

@description('Network security group name')
param nsgName string

@description('Virtual network address prefix')
param vnetAddressPrefix string

@description('Subnet address prefix')
param subnetAddressPrefix string

@description('Tags to apply to resources')
param tags object

// ============== Network Security Group ==============
resource nsg 'Microsoft.Network/networkSecurityGroups@2023-04-01' = {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowRdpInbound'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '3389'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
          description: 'Allow RDP access for AVD'
        }
      }
      {
        name: 'AllowAzureGatewayInbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'GatewayManager'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 110
          direction: 'Inbound'
          description: 'Allow Azure Gateway Manager'
        }
      }
      {
        name: 'AllowAzureLoadBalancerInbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 120
          direction: 'Inbound'
          description: 'Allow Azure Load Balancer'
        }
      }
    ]
  }
  tags: tags
}

// ============== Virtual Network ==============
resource vnet 'Microsoft.Network/virtualNetworks@2023-04-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: subnetName
        properties: {
          addressPrefix: subnetAddressPrefix
          networkSecurityGroup: {
            id: nsg.id
          }
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Disabled'
        }
      }
    ]
    enableDdosProtection: false
  }
  tags: tags
}

// ============== Outputs ==============
output vnetId string = vnet.id
output vnetName string = vnet.name
output subnetId string = vnet.properties.subnets[0].id
output subnetName string = subnetName
output nsgId string = nsg.id
