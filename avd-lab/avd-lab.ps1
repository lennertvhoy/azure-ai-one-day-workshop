#!/usr/bin/env pwsh
#Requires -Version 7.0
<#
.SYNOPSIS
    AVD Lab Lifecycle Tool - Manage Azure Virtual Desktop lab environments

.DESCRIPTION
    A CLI tool to provision and tear down Azure Virtual Desktop (AVD) environments
    for course testing with minimal manual steps and clear cost controls.

.EXAMPLE
    ./avd-lab.ps1 validate --config config/lab-dev.json
    ./avd-lab.ps1 create --config config/lab-dev.json --participant jeff --ttl 8h
    ./avd-lab.ps1 status --participant jeff
    ./avd-lab.ps1 status --lab-id azure-jeff-202602120930-abc1
    ./avd-lab.ps1 destroy --participant jeff --yes
    ./avd-lab.ps1 estimate-cost --config config/lab-dev.json --hours 8

.NOTES
    Exit codes:
    0 - Success
    1 - Validation/config error
    2 - Azure API/deploy failure
    3 - Safety check blocked action
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet('validate', 'create', 'destroy', 'status', 'estimate-cost', 'help')]
    [string]$Command = 'help',

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

# ============== Configuration ==============
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOGS_DIR = Join-Path $SCRIPT_DIR "logs/avd-lab"
$CONFIG_DIR = Join-Path $SCRIPT_DIR "config"
$IAC_DIR = Join-Path $SCRIPT_DIR "iac"

# Exit codes
$EXIT_SUCCESS = 0
$EXIT_VALIDATION_ERROR = 1
$EXIT_AZURE_ERROR = 2
$EXIT_SAFETY_BLOCKED = 3

# ============== Logging Functions ==============
function Initialize-Logging {
    if (-not (Test-Path $LOGS_DIR)) {
        New-Item -ItemType Directory -Path $LOGS_DIR -Force | Out-Null
    }
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $script:LogFile = Join-Path $LOGS_DIR "$timestamp.log"
}

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR', 'DEBUG')]
        [string]$Level = 'INFO'
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
    $logEntry = @{
        timestamp = $timestamp
        level = $Level
        message = $Message
    }
    
    # JSON log
    $jsonLog = $logEntry | ConvertTo-Json -Compress
    Add-Content -Path $script:LogFile -Value $jsonLog
    
    # Human-readable output
    $color = switch ($Level) {
        'INFO' { 'Cyan' }
        'WARN' { 'Yellow' }
        'ERROR' { 'Red' }
        'DEBUG' { 'Gray' }
    }
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error-Exit {
    param(
        [string]$Message,
        [int]$ExitCode = $EXIT_VALIDATION_ERROR
    )
    Write-Log -Message $Message -Level 'ERROR'
    exit $ExitCode
}

# ============== Argument Parsing ==============
function Parse-Arguments {
    param([string[]]$Args)
    
    $result = @{
        config = $null
        name = $null
        lab_id = $null
        participant = $null
        ttl = $null
        hours = $null
        yes = $false
        dry_run = $false
    }
    
    for ($i = 0; $i -lt $Args.Count; $i++) {
        switch ($Args[$i]) {
            '--config' { $result.config = $Args[++$i] }
            '--name' { $result.name = $Args[++$i] }
            '--lab-id' { $result.lab_id = $Args[++$i] }
            '--participant' { $result.participant = $Args[++$i] }
            '--ttl' { $result.ttl = $Args[++$i] }
            '--hours' { $result.hours = [int]$Args[++$i] }
            '--yes' { $result.yes = $true }
            '--dry-run' { $result.dry_run = $true }
            '-y' { $result.yes = $true }
        }
    }
    
    # --lab-id takes precedence over --name
    if ($result.lab_id) {
        $result.name = $result.lab_id
    }
    
    return $result
}

# ============== Lab ID Generation ==============
function New-LabId {
    param(
        [string]$Course,
        [string]$Participant
    )
    
    $timestamp = Get-Date -Format "yyyyMMddHHmm"
    $rand4 = -join ((48..57) + (97..122) | Get-Random -Count 4 | ForEach-Object { [char]$_ })
    return "$Course-$Participant-$timestamp-$rand4"
}

# ============== Preflight Checks ==============
function Test-ExistingLabs {
    param(
        [string]$Participant
    )
    
    Write-Log "Checking for existing labs for participant: $Participant"
    
    # Check for existing resources with same participant tag that are not expired
    $existingLabs = az resource list `
        --tag "participant=$Participant" `
        --query "[?tags.'managed-by'=='avd-lab-tool']" `
        -o json 2>$null | ConvertFrom-Json
    
    $activeLabs = $existingLabs | Where-Object {
        $_.tags.expiry -and [DateTime]::Parse($_.tags.expiry) -gt (Get-Date)
    } | Select-Object -ExpandProperty tags -Unique | ForEach-Object { $_.'lab-id' } | Where-Object { $_ } | Sort-Object -Unique
    
    if ($activeLabs) {
        Write-Log "Active lab(s) already exist for participant '$Participant':" -Level 'ERROR'
        $activeLabs | ForEach-Object { Write-Host "  - $_" }
        Write-Error-Exit "Destroy existing lab(s) first or use a different participant slug" $EXIT_SAFETY_BLOCKED
    }
    
    Write-Success "No active labs found for participant: $Participant"
}

function Test-LabIdExists {
    param(
        [string]$LabId
    )
    
    Write-Log "Checking if lab-id '$LabId' already exists..."
    
    $existing = az resource list `
        --tag "lab-id=$LabId" `
        --query "length(@)" `
        -o tsv 2>$null
    
    if ($existing -and [int]$existing -gt 0) {
        Write-Error-Exit "Lab with id '$LabId' already exists. This should not happen - please report." $EXIT_SAFETY_BLOCKED
    }
    
    Write-Success "Lab-id '$LabId' is available"
}

# ============== Configuration Loading ==============
function Load-Config {
    param([string]$ConfigPath)
    
    if (-not $ConfigPath) {
        Write-Error-Exit "Configuration file path is required. Use --config <path>"
    }
    
    $fullPath = if (Test-Path $ConfigPath -PathType Absolute) { 
        $ConfigPath 
    } else { 
        Join-Path $SCRIPT_DIR $ConfigPath 
    }
    
    if (-not (Test-Path $fullPath)) {
        Write-Error-Exit "Configuration file not found: $fullPath"
    }
    
    $configContent = Get-Content $fullPath -Raw
    $config = $configContent | ConvertFrom-Json
    
    # Expand environment variables in config values
    $config.parameters.PSObject.Properties | ForEach-Object {
        if ($_.Value.value -is [string] -and $_.Value.value -match '^\$\{(.+)\}$') {
            $envVar = $Matches[1]
            $defaultValue = $null
            if ($envVar -match '(.+):-(.+)') {
                $envVar = $Matches[1]
                $defaultValue = $Matches[2]
            }
            $envValue = [Environment]::GetEnvironmentVariable($envVar)
            $_.Value.value = if ($envValue) { $envValue } else { $defaultValue }
        }
    }
    
    return $config.parameters
}

# ============== Azure Prerequisites Check ==============
function Test-AzurePrerequisites {
    Write-Log "Checking Azure prerequisites..."
    
    # Check Azure CLI
    $azCli = Get-Command az -ErrorAction SilentlyContinue
    if (-not $azCli) {
        Write-Error-Exit "Azure CLI not found. Please install: https://docs.microsoft.com/cli/azure/install-azure-cli"
    }
    Write-Success "Azure CLI found"
    
    # Check if logged in
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        Write-Error-Exit "Not logged in to Azure. Run: az login"
    }
    Write-Success "Logged in as: $($account.user.name)"
    
    # Check subscription
    $subscriptionId = $account.id
    Write-Success "Subscription: $subscriptionId ($($account.name))"
    
    # Check required providers
    $requiredProviders = @(
        'Microsoft.DesktopVirtualization',
        'Microsoft.Compute',
        'Microsoft.Network',
        'Microsoft.Resources',
        'Microsoft.Storage'
    )
    
    foreach ($provider in $requiredProviders) {
        $registered = az provider show --namespace $provider --query "registrationState" -o tsv 2>$null
        if ($registered -ne 'Registered') {
            Write-Log "Registering provider: $provider" -Level 'WARN'
            az provider register --namespace $provider
        }
        Write-Success "Provider registered: $provider"
    }
    
    # Check Bicep
    $bicep = az bicep version 2>$null
    if (-not $bicep) {
        Write-Log "Installing Bicep..." -Level 'WARN'
        az bicep install
    }
    Write-Success "Bicep available: $bicep"
    
    return @{
        subscriptionId = $subscriptionId
        account = $account
    }
}

function Test-QuotaAvailability {
    param(
        [string]$Location,
        [string]$VmSize,
        [int]$Count
    )
    
    Write-Log "Checking quota for $VmSize in $Location..."
    
    $usage = az vm list-usage --location $Location --query "[?name.value=='$VmSize']" -o json 2>$null | ConvertFrom-Json
    
    if ($usage) {
        $available = $usage[0].limit - $usage[0].currentValue
        if ($available -lt $Count) {
            Write-Error-Exit "Insufficient quota for $VmSize in $Location. Available: $available, Required: $Count"
        }
        Write-Success "Quota available: $available VMs of type $VmSize"
    } else {
        Write-Log "Could not verify quota for $VmSize. Proceeding..." -Level 'WARN'
    }
}

function Test-NetworkCollision {
    param(
        [string]$AddressPrefix,
        [string]$Location
    )
    
    Write-Log "Checking for network collisions with $AddressPrefix..."
    
    $vnets = az network vnet list --query "[?location=='$Location']" -o json 2>$null | ConvertFrom-Json
    
    foreach ($vnet in $vnets) {
        foreach ($prefix in $vnet.addressSpace.addressPrefixes) {
            if ($prefix -eq $AddressPrefix) {
                Write-Error-Exit "Network collision detected: $AddressPrefix is already used by $($vnet.name)"
            }
        }
    }
    
    Write-Success "No network collisions detected"
}

# ============== Validate Command ==============
function Invoke-Validate {
    param($Args)
    
    Write-Log "Starting validation..."
    
    $config = Load-Config -ConfigPath $Args.config
    $azure = Test-AzurePrerequisites
    
    # Validate config values
    $location = $config.location.value
    $vmSize = $config.vmSize.value
    $vmCount = $config.numberOfSessionHosts.value
    $vnetPrefix = $config.vnetAddressPrefix.value
    
    Test-QuotaAvailability -Location $location -VmSize $vmSize -Count $vmCount
    Test-NetworkCollision -AddressPrefix $vnetPrefix -Location $location
    
    Write-Log "Validation completed successfully"
    Write-Success "All prerequisites validated"
    
    return $EXIT_SUCCESS
}

# ============== Create Command ==============
function Invoke-Create {
    param($Args)
    
    Write-Log "Starting AVD lab creation..."
    
    # Require participant slug
    if (-not $Args.participant) {
        Write-Error-Exit "Participant slug is required. Use --participant <slug>"
    }
    
    # Validate participant slug format (lowercase alphanumeric and hyphens only)
    if ($Args.participant -notmatch '^[a-z0-9-]+$') {
        Write-Error-Exit "Participant slug must be lowercase alphanumeric with hyphens only"
    }
    
    $config = Load-Config -ConfigPath $Args.config
    $azure = Test-AzurePrerequisites
    
    # Get course name from config
    $course = if ($config.tags.value.course) { $config.tags.value.course } else { "azure" }
    # Sanitize course name for lab-id
    $course = $course.ToLower() -replace '[^a-z0-9-]', ''
    
    # Generate unique lab-id
    $labId = New-LabId -Course $course -Participant $Args.participant
    
    Write-Log "Generated lab-id: $labId"
    
    # Preflight checks
    Test-ExistingLabs -Participant $Args.participant
    Test-LabIdExists -LabId $labId
    
    # Calculate expiry time
    $ttl = if ($Args.ttl) { $Args.ttl } else { "8h" }
    $ttlMatch = $ttl -match '^(\d+)(h|d)$'
    if (-not $ttlMatch) {
        Write-Error-Exit "Invalid TTL format. Use format like '8h' or '1d'"
    }
    
    $ttlValue = [int]$Matches[1]
    $ttlUnit = $Matches[2]
    $expiry = if ($ttlUnit -eq 'h') {
        (Get-Date).AddHours($ttlValue).ToString("yyyy-MM-ddTHH:mm:ssZ")
    } else {
        (Get-Date).AddDays($ttlValue).ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    
    Write-Log "Lab will expire at: $expiry"
    
    # Override config with CLI args
    $rgName = $labId
    $location = $config.location.value
    
    # Get owner and cost center from config
    $owner = if ($config.tags.value.owner) { $config.tags.value.owner } else { "lab-admin" }
    $costCenter = if ($config.tags.value.costCenter) { $config.tags.value.costCenter } else { "training" }
    
    # Generate admin password
    $adminPassword = -join ((33..126) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
    # Ensure it meets complexity requirements
    $adminPassword = $adminPassword + "A1!"
    
    # Build tags with lab-id and participant
    $tags = @{
        "managed-by" = "avd-lab-tool"
        "lab-id" = $labId
        "participant" = $Args.participant
        "course" = $course
        "owner" = $owner
        "costCenter" = $costCenter
        "expiry" = $expiry
    }
    
    # Prepare parameters
    $parameters = @{
        resourceGroupName = $rgName
        location = $location
        namingPrefix = $labId
        namingSuffix = $labId
        vmSize = $config.vmSize.value
        vmImage = $config.vmImage.value
        hostPoolType = $config.hostPoolType.value
        loadBalancerType = $config.loadBalancerType.value
        maxSessionsPerHost = $config.maxSessionsPerHost.value
        numberOfSessionHosts = $config.numberOfSessionHosts.value
        vnetAddressPrefix = $config.vnetAddressPrefix.value
        subnetAddressPrefix = $config.subnetAddressPrefix.value
        aadJoinType = $config.aadJoinType.value
        adminPassword = $adminPassword
        tags = $tags
        expiry = $expiry
    }
    
    $paramsFile = Join-Path $SCRIPT_DIR "temp-params.json"
    $parameters | ConvertTo-Json -Depth 10 | Set-Content $paramsFile
    
    if ($Args.dry_run) {
        Write-Log "Dry run mode - would deploy with parameters:"
        $parameters | ConvertTo-Json -Depth 10 | Write-Host
        Remove-Item $paramsFile -Force
        return $EXIT_SUCCESS
    }
    
    # Deploy
    Write-Log "Deploying AVD lab: $labId"
    
    $bicepFile = Join-Path $IAC_DIR "main.bicep"
    $deploymentName = "avd-lab-$labId"
    
    $deployment = az deployment sub create `
        --location $location `
        --template-file $bicepFile `
        --parameters "@$paramsFile" `
        --name $deploymentName `
        -o json 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Remove-Item $paramsFile -Force
        Write-Error-Exit "Deployment failed: $deployment" -ExitCode $EXIT_AZURE_ERROR
    }
    
    Remove-Item $paramsFile -Force
    
    $outputs = $deployment | ConvertFrom-Json | Select-Object -ExpandProperty properties -ExpandProperty outputs
    
    # Output results
    Write-Success "AVD Lab created successfully!"
    Write-Host ""
    Write-Host "Lab ID: $labId"
    Write-Host "Participant: $($Args.participant)"
    Write-Host "Resource Group: $($outputs.resourceGroupName.value)"
    Write-Host "Host Pool: $($outputs.hostPoolName.value)"
    Write-Host "Workspace: $($outputs.workspaceName.value)"
    Write-Host "Workspace URL: $($outputs.workspaceUrl.value)"
    Write-Host "Expiry: $($outputs.expiry.value)"
    Write-Host ""
    Write-Host "To destroy this lab, run:" -ForegroundColor Yellow
    Write-Host "  ./avd-lab.ps1 destroy --lab-id $labId --yes" -ForegroundColor Yellow
    
    # Estimate cost
    $estimatedCost = Estimate-Cost -Config $config -Hours $ttlValue
    Write-Host ""
    Write-Host "Estimated cost for TTL period: `$$estimatedCost" -ForegroundColor Cyan
    
    return $EXIT_SUCCESS
}

# ============== Destroy Command ==============
function Invoke-Destroy {
    param($Args)
    
    Write-Log "Starting AVD lab destruction..."
    
    $labId = $null
    $participant = $null
    
    if ($Args.name) {
        # --name is now --lab-id for backward compatibility
        $labId = $Args.name
    }
    
    if ($Args.participant) {
        $participant = $Args.participant
    }
    
    if (-not $labId -and -not $participant) {
        Write-Error-Exit "Lab ID or participant is required. Use --lab-id <id> or --participant <slug>"
    }
    
    Test-AzurePrerequisites
    
    $rgName = $null
    
    if ($labId) {
        # Find by lab-id tag
        Write-Log "Looking up lab by lab-id: $labId"
        
        $labResources = az resource list --tag "lab-id=$labId" --tag "managed-by=avd-lab-tool" -o json 2>$null | ConvertFrom-Json
        
        if ($labResources.Count -eq 0) {
            # Try as resource group name for backward compatibility
            $rg = az group show --name $labId 2>$null | ConvertFrom-Json
            if ($rg) {
                $rgName = $labId
            } else {
                Write-Error-Exit "No resources found with lab-id='$labId'"
            }
        } else {
            # Get resource group from first resource
            $rgName = $labResources[0].resourceGroup
        }
    } else {
        # Find by participant (only if single active lab)
        Write-Log "Looking up lab by participant: $participant"
        
        $labResources = az resource list --tag "participant=$participant" --tag "managed-by=avd-lab-tool" -o json 2>$null | ConvertFrom-Json
        
        if ($labResources.Count -eq 0) {
            Write-Error-Exit "No resources found with participant='$participant'"
        }
        
        # Get unique lab-ids
        $labIds = $labResources | ForEach-Object { $_.tags.'lab-id' } | Where-Object { $_ } | Sort-Object -Unique
        
        if ($labIds.Count -gt 1) {
            Write-Log "Multiple labs found for participant '$participant':" -Level 'ERROR'
            $labIds | ForEach-Object { Write-Host "  - $_" }
            Write-Error-Exit "Specify --lab-id to target a specific lab" $EXIT_SAFETY_BLOCKED
        }
        
        $labId = $labIds | Select-Object -First 1
        $rgName = $labResources[0].resourceGroup
    }
    
    # Verify it's managed by this tool
    $rg = az group show --name $rgName 2>$null | ConvertFrom-Json
    if (-not $rg) {
        Write-Error-Exit "Resource group '$rgName' not found"
    }
    
    $managedBy = $rg.tags.'managed-by'
    if ($managedBy -ne 'avd-lab-tool') {
        Write-Error-Exit "Resource group '$rgName' is not managed by avd-lab-tool. Refusing to delete for safety." -ExitCode $EXIT_SAFETY_BLOCKED
    }
    
    # Get lab-id from RG if not set
    if (-not $labId) {
        $labId = $rg.tags.'lab-id'
    }
    
    # Show delete plan
    Write-Host ""
    Write-Host "Resources to be deleted:" -ForegroundColor Yellow
    Write-Host "  Lab ID: $labId"
    Write-Host "  Resource Group: $rgName"
    
    $resources = az resource list --resource-group $rgName -o json 2>$null | ConvertFrom-Json
    $resources | ForEach-Object {
        Write-Host "  - $($_.type): $($_.name)"
    }
    Write-Host ""
    
    # Confirm deletion
    if (-not $Args.yes) {
        $confirm = Read-Host "Are you sure you want to delete these resources? (yes/no)"
        if ($confirm -ne 'yes') {
            Write-Log "Deletion cancelled by user"
            return $EXIT_SUCCESS
        }
    }
    
    # Delete resource group
    Write-Log "Deleting resource group: $rgName"
    
    az group delete --name $rgName --yes --no-wait
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Exit "Failed to delete resource group" -ExitCode $EXIT_AZURE_ERROR
    }
    
    # Poll for completion
    Write-Log "Deletion in progress..."
    $maxWait = 300  # 5 minutes
    $waited = 0
    
    while ($waited -lt $maxWait) {
        $rg = az group show --name $rgName 2>$null
        if (-not $rg) {
            break
        }
        Start-Sleep -Seconds 10
        $waited += 10
        Write-Host "." -NoNewline
    }
    Write-Host ""
    
    # Scan for orphaned resources
    Write-Log "Scanning for orphaned resources..."
    $orphaned = az resource list --tag "lab-id=$labId" -o json 2>$null | ConvertFrom-Json
    
    if ($orphaned.Count -gt 0) {
        Write-Log "Found $($orphaned.Count) orphaned resources:" -Level 'WARN'
        $orphaned | ForEach-Object {
            Write-Host "  - $($_.type): $($_.name)" -ForegroundColor Yellow
        }
    } else {
        Write-Success "No orphaned resources found"
    }
    
    Write-Success "AVD Lab destroyed successfully"
    
    return $EXIT_SUCCESS
}

# ============== Status Command ==============
function Invoke-Status {
    param($Args)
    
    Write-Log "Getting AVD lab status..."
    
    $labId = $null
    $participant = $null
    
    if ($Args.name) {
        $labId = $Args.name
    }
    
    if ($Args.participant) {
        $participant = $Args.participant
    }
    
    if (-not $labId -and -not $participant) {
        Write-Error-Exit "Lab ID or participant is required. Use --lab-id <id> or --participant <slug>"
    }
    
    Test-AzurePrerequisites
    
    $rgName = $null
    
    if ($labId) {
        # Find by lab-id tag
        $labResources = az resource list --tag "lab-id=$labId" --tag "managed-by=avd-lab-tool" -o json 2>$null | ConvertFrom-Json
        
        if ($labResources.Count -eq 0) {
            # Try as resource group name for backward compatibility
            $rg = az group show --name $labId 2>$null | ConvertFrom-Json
            if ($rg) {
                $rgName = $labId
            } else {
                Write-Error-Exit "Lab '$labId' not found"
            }
        } else {
            $rgName = $labResources[0].resourceGroup
        }
    } else {
        # Find by participant
        $labResources = az resource list --tag "participant=$participant" --tag "managed-by=avd-lab-tool" -o json 2>$null | ConvertFrom-Json
        
        if ($labResources.Count -eq 0) {
            Write-Error-Exit "No lab found for participant '$participant'"
        }
        
        # Get unique lab-ids
        $labIds = $labResources | ForEach-Object { $_.tags.'lab-id' } | Where-Object { $_ } | Sort-Object -Unique
        
        if ($labIds.Count -gt 1) {
            Write-Log "Multiple labs found for participant '$participant':" -Level 'WARN'
            $labIds | ForEach-Object { Write-Host "  - $_" }
            Write-Error-Exit "Specify --lab-id to view a specific lab" $EXIT_SAFETY_BLOCKED
        }
        
        $labId = $labIds | Select-Object -First 1
        $rgName = $labResources[0].resourceGroup
    }
    
    # Check resource group
    $rg = az group show --name $rgName 2>$null | ConvertFrom-Json
    if (-not $rg) {
        Write-Error-Exit "Lab '$labId' not found"
    }
    
    # Get lab-id from RG if not set
    if (-not $labId) {
        $labId = $rg.tags.'lab-id'
    }
    
    Write-Host ""
    Write-Host "AVD Lab Status" -ForegroundColor Cyan
    Write-Host "================================"
    Write-Host "Lab ID: $labId"
    Write-Host "Resource Group: $($rg.name)"
    Write-Host "Location: $($rg.location)"
    Write-Host "Tags:"
    $rg.tags.PSObject.Properties | ForEach-Object {
        Write-Host "  $($_.Name): $($_.Value)"
    }
    
    # Get host pool
    $hostPools = az desktopvirtualization host-pool list --resource-group $rgName -o json 2>$null | ConvertFrom-Json
    if ($hostPools) {
        Write-Host ""
        Write-Host "Host Pools:" -ForegroundColor Cyan
        $hostPools | ForEach-Object {
            Write-Host "  Name: $($_.name)"
            Write-Host "  Type: $($_.properties.hostPoolType)"
            Write-Host "  Max Sessions: $($_.properties.maxSessionLimit)"
        }
    }
    
    # Get session hosts
    if ($hostPools) {
        Write-Host ""
        Write-Host "Session Hosts:" -ForegroundColor Cyan
        foreach ($hp in $hostPools) {
            $sessionHosts = az desktopvirtualization session-host list --resource-group $rgName --host-pool-name $hp.name -o json 2>$null | ConvertFrom-Json
            $sessionHosts | ForEach-Object {
                $status = $_.properties.status
                $statusColor = if ($status -eq 'Available') { 'Green' } else { 'Yellow' }
                Write-Host "  $($_.name): " -NoNewline
                Write-Host $status -ForegroundColor $statusColor
            }
        }
    }
    
    # Get VMs
    $vms = az vm list --resource-group $rgName -o json 2>$null | ConvertFrom-Json
    if ($vms) {
        Write-Host ""
        Write-Host "Virtual Machines:" -ForegroundColor Cyan
        $vms | ForEach-Object {
            $powerState = az vm get-instance-view --name $_.name --resource-group $rgName --query "instanceView.statuses[?code=='PowerState/running']" -o tsv 2>$null
            $running = $powerState -match 'running'
            Write-Host "  $($_.name): " -NoNewline
            if ($running) {
                Write-Host "Running" -ForegroundColor Green
            } else {
                Write-Host "Stopped" -ForegroundColor Yellow
            }
        }
    }
    
    # Check expiry
    if ($rg.tags.expiry) {
        $expiry = [DateTime]$rg.tags.expiry
        $now = Get-Date
        if ($expiry -lt $now) {
            Write-Host ""
            Write-Host "⚠ Lab has expired! Consider destroying it." -ForegroundColor Red
        } else {
            $remaining = $expiry - $now
            Write-Host ""
            Write-Host "Time remaining: $($remaining.ToString('dd\d hh\h mm\m'))" -ForegroundColor Cyan
        }
    }
    
    return $EXIT_SUCCESS
}

# ============== Estimate Cost Command ==============
function Estimate-Cost {
    param(
        $Config,
        [int]$Hours = 8
    )
    
    # Rough cost estimates (USD/hour) - these are approximate
    $vmCosts = @{
        'Standard_D2s_v3' = 0.10
        'Standard_D4s_v3' = 0.20
        'Standard_D8s_v3' = 0.40
        'Standard_D2s_v4' = 0.11
        'Standard_D4s_v4' = 0.22
        'Standard_D8s_v4' = 0.44
        'Standard_D2s_v5' = 0.12
        'Standard_D4s_v5' = 0.24
        'Standard_D8s_v5' = 0.48
    }
    
    $vmSize = $Config.vmSize.value
    $vmCount = $Config.numberOfSessionHosts.value
    
    $hourlyRate = if ($vmCosts.ContainsKey($vmSize)) { $vmCosts[$vmSize] } else { 0.15 }
    
    # Add storage cost (approx $0.10/GB/month for Premium SSD)
    $storageCost = 127 * 0.10 / 730 * $vmCount  # 127GB disk per VM
    
    # Add network cost (approx $0.01/hour)
    $networkCost = 0.01
    
    $totalHourly = ($hourlyRate * $vmCount) + $storageCost + $networkCost
    $totalCost = $totalHourly * $Hours
    
    return [math]::Round($totalCost, 2)
}

function Invoke-EstimateCost {
    param($Args)
    
    Write-Log "Estimating AVD lab cost..."
    
    $config = Load-Config -ConfigPath $Args.config
    $hours = if ($Args.hours) { $Args.hours } else { 8 }
    
    $cost = Estimate-Cost -Config $config -Hours $hours
    
    Write-Host ""
    Write-Host "Cost Estimate" -ForegroundColor Cyan
    Write-Host "============="
    Write-Host "VM Size: $($config.vmSize.value)"
    Write-Host "Number of VMs: $($config.numberOfSessionHosts.value)"
    Write-Host "Duration: $hours hours"
    Write-Host ""
    Write-Host "Estimated Total Cost: `$$cost USD" -ForegroundColor Green
    Write-Host ""
    Write-Host "Note: This is a rough estimate. Actual costs may vary based on:" -ForegroundColor Yellow
    Write-Host "  - Region pricing differences"
    Write-Host "  - Data transfer costs"
    Write-Host "  - Actual usage patterns"
    
    return $EXIT_SUCCESS
}

# ============== Help ==============
function Show-Help {
    Write-Host @"
AVD Lab Lifecycle Tool - Manage Azure Virtual Desktop lab environments

USAGE:
    ./avd-lab.ps1 <command> [options]

COMMANDS:
    validate        Validate prerequisites and configuration
    create          Create a new AVD lab environment
    destroy         Destroy an AVD lab environment
    status          Show status of an AVD lab environment
    estimate-cost   Estimate cost for running a lab
    help            Show this help message

OPTIONS:
    --config <path>       Path to configuration file (required for validate, create, estimate-cost)
    --participant <slug>  Participant identifier (required for create, can be used for destroy/status)
    --lab-id <id>         Lab identifier (can be used for destroy/status instead of participant)
    --name <name>         [Deprecated] Use --lab-id instead
    --ttl <duration>      Time-to-live for the lab (e.g., '8h', '1d')
    --hours <number>      Hours for cost estimation
    --yes                 Skip confirmation prompts
    --dry-run             Show what would be done without making changes

EXAMPLES:
    # Validate prerequisites
    ./avd-lab.ps1 validate --config config/lab-dev.json

    # Create a lab for participant 'jeff' with 8-hour TTL
    ./avd-lab.ps1 create --config config/lab-dev.json --participant jeff --ttl 8h

    # Check lab status by participant
    ./avd-lab.ps1 status --participant jeff

    # Check lab status by lab-id
    ./avd-lab.ps1 status --lab-id azure-jeff-202602120930-abc1

    # Estimate cost for 8 hours
    ./avd-lab.ps1 estimate-cost --config config/lab-dev.json --hours 8

    # Destroy a lab by participant (with confirmation)
    ./avd-lab.ps1 destroy --participant jeff

    # Destroy a lab by lab-id (skip confirmation)
    ./avd-lab.ps1 destroy --lab-id azure-jeff-202602120930-abc1 --yes

ENVIRONMENT VARIABLES:
    AZ_SUBSCRIPTION_ID   Azure subscription ID
    AZ_LOCATION          Azure region
    LAB_NAME             Default lab name
    OWNER                Owner tag value
    COURSE               Course tag value
    COST_CENTER          Cost center tag value

EXIT CODES:
    0  Success
    1  Validation/config error
    2  Azure API/deploy failure
    3  Safety check blocked action

"@
}

# ============== Main ==============
Initialize-Logging

$parsedArgs = Parse-Arguments -Args $RemainingArgs

switch ($Command) {
    'validate' { exit (Invoke-Validate -Args $parsedArgs) }
    'create' { exit (Invoke-Create -Args $parsedArgs) }
    'destroy' { exit (Invoke-Destroy -Args $parsedArgs) }
    'status' { exit (Invoke-Status -Args $parsedArgs) }
    'estimate-cost' { exit (Invoke-EstimateCost -Args $parsedArgs) }
    'help' { Show-Help; exit $EXIT_SUCCESS }
}
