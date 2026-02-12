// Host Pool Module - AVD Host Pool Configuration

// ============== Parameters ==============
@description('Azure region for deployment')
param location string

@description('Host pool name')
param hostPoolName string

@description('Host pool type: Pooled or Personal')
@allowed([
  'Pooled'
  'Personal'
])
param hostPoolType string = 'Pooled'

@description('Load balancer type: BreadthFirst, DepthFirst, or Persistent')
@allowed([
  'BreadthFirst'
  'DepthFirst'
  'Persistent'
])
param loadBalancerType string = 'BreadthFirst'

@description('Maximum sessions per host')
param maxSessionsPerHost int = 10

@description('Preferred app group type')
param preferredAppGroupType string = 'Desktop'

@description('Custom RDP properties')
param customRdpProperties string = 'drivestoredirect:s:*;audiomode:i:0;videoplaybackmode:i:1;redirectclipboard:i:1;redirectprinters:i:1;devicestoredirect:s:*;redirectcomports:i:1;redirectsmartcards:i:1;usbdevicestoredirect:s:*;enablecredsspsupport:i:1;use multimon:i:1'

@description('Validation environment')
param validationEnv bool = false

@description('Registration token expiration time (ISO8601)')
param registrationTokenExpiration string = dateTimeAdd(utcNow(), 'PT8H')

@description('Tags to apply to resources')
param tags object

// ============== Host Pool ==============
resource hostPool 'Microsoft.DesktopVirtualization/hostPools@2023-09-05' = {
  name: hostPoolName
  location: location
  properties: {
    hostPoolType: hostPoolType
    loadBalancerType: loadBalancerType
    preferredAppGroupType: preferredAppGroupType
    maxSessionLimit: maxSessionsPerHost
    customRdpProperty: customRdpProperties
    validationEnvironment: validationEnv
    ring: validationEnv ? 1 : 0
    registrationInfo: {
      expirationTime: registrationTokenExpiration
      registrationTokenOperation: 'Update'
    }
    ssoadfsAuthority: ''
    ssoClientId: ''
    ssoClientSecretKeyVaultPath: ''
    ssoSecretType: 'SharedKey'
    startVMOnConnect: true
  }
  tags: tags
}

// ============== Outputs ==============
output hostPoolId string = hostPool.id
output hostPoolName string = hostPool.name
