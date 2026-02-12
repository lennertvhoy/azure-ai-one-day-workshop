# AVD Lab Troubleshooting Guide

This guide covers common issues and solutions when using the AVD Lab Lifecycle Tool.

## Table of Contents

1. [Azure CLI Issues](#azure-cli-issues)
2. [Authentication Issues](#authentication-issues)
3. [Deployment Failures](#deployment-failures)
4. [Quota and Capacity Issues](#quota-and-capacity-issues)
5. [Network Issues](#network-issues)
6. [Session Host Issues](#session-host-issues)
7. [PowerShell-Specific Issues](#powershell-specific-issues)
8. [Bash/Linux-Specific Issues](#bashlinux-specific-issues)
9. [Cleanup and Orphaned Resources](#cleanup-and-orphaned-resources)

---

## Azure CLI Issues

### Issue: Azure CLI not found

**Error Message:**
```
Azure CLI not found. Please install: https://docs.microsoft.com/cli/azure/install-azure-cli
```

**Solution:**
Install Azure CLI for your platform:

```bash
# Windows (PowerShell)
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'
Remove-Item .\AzureCLI.msi

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Linux (RHEL/CentOS)
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
sudo dnf install -y https://packages.microsoft.com/config/rhel/8/packages-microsoft-prod.rpm
sudo dnf install azure-cli

# macOS
brew install azure-cli
```

### Issue: Azure CLI version outdated

**Error Message:**
```
Your Azure CLI version is outdated. Please update to the latest version.
```

**Solution:**
```bash
# Update Azure CLI
az upgrade

# Verify version
az version
```

---

## Authentication Issues

### Issue: Not logged in to Azure

**Error Message:**
```
Not logged in to Azure. Run: az login
```

**Solution:**
```bash
# Interactive login
az login

# Login with device code (for WSL or headless environments)
az login --use-device-code

# Login with service principal
az login --service-principal -u <app-id> -p <password-or-cert> --tenant <tenant-id>
```

### Issue: Wrong subscription selected

**Error Message:**
```
Subscription 'xxx' does not have permission to access resource group 'yyy'
```

**Solution:**
```bash
# List available subscriptions
az account list --output table

# Set the correct subscription
az account set --subscription "<subscription-id-or-name>"

# Verify current subscription
az account show
```

### Issue: Insufficient permissions

**Error Message:**
```
The client 'xxx' with object id 'xxx' does not have authorization to perform action 'Microsoft.Resources/deployments/write'
```

**Solution:**
Ensure your account has the required roles:
- **Contributor** or **Owner** on the subscription or resource group
- **User Access Administrator** (if assigning users to AVD)

```bash
# Check your role assignments
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv)

# Request access from your Azure administrator
```

---

## Deployment Failures

### Issue: Bicep compilation error

**Error Message:**
```
Error BCPxxx: ...
```

**Solution:**
1. Ensure Bicep is installed:
   ```bash
   az bicep install
   az bicep upgrade
   ```

2. Validate the Bicep template:
   ```bash
   az deployment sub validate --location westeurope --template-file iac/main.bicep --parameters @config/lab-dev.json
   ```

### Issue: Deployment timeout

**Error Message:**
```
Deployment timed out. The deployment took longer than expected.
```

**Solution:**
1. Check deployment status:
   ```bash
   az deployment sub list --query "[?properties.provisioningState=='Running']"
   ```

2. Session host VMs can take 15-30 minutes to deploy. Wait and check status:
   ```bash
   ./avd-lab.sh status --name <lab-name>
   ```

### Issue: Resource provider not registered

**Error Message:**
```
The subscription is not registered to use namespace 'Microsoft.DesktopVirtualization'
```

**Solution:**
Register the required providers:
```bash
az provider register --namespace Microsoft.DesktopVirtualization
az provider register --namespace Microsoft.Compute
az provider register --namespace Microsoft.Network
az provider register --namespace Microsoft.Storage

# Wait for registration to complete
az provider show --namespace Microsoft.DesktopVirtualization --query registrationState
```

---

## Quota and Capacity Issues

### Issue: Insufficient VM quota

**Error Message:**
```
Operation could not be completed as it results in exceeding Approved standard DSv3 Family vCPUs quota
```

**Solution:**
1. Check current quota:
   ```bash
   az vm list-usage --location westeurope --output table
   ```

2. Request quota increase:
   - Go to Azure Portal → Subscriptions → Usage + quotas
   - Or use Azure CLI:
     ```bash
     az quota request create --scope /subscriptions/<sub-id> --resource-name standardDSv3Family --namespace Microsoft.Compute --value 10
     ```

3. Or use a different VM size that has available quota.

### Issue: Region capacity unavailable

**Error Message:**
```
The requested VM size is not available in the current region
```

**Solution:**
1. Check available VM sizes in the region:
   ```bash
   az vm list-sizes --location westeurope --output table
   ```

2. Try a different region:
   ```bash
   export AZ_LOCATION="northeurope"
   ./avd-lab.sh create --config config/lab-dev.json --name my-lab
   ```

---

## Network Issues

### Issue: Address space collision

**Error Message:**
```
Network collision detected: 10.0.0.0/16 is already used by 'existing-vnet'
```

**Solution:**
1. Use a different address space in your config:
   ```json
   {
     "vnetAddressPrefix": { "value": "10.1.0.0/16" },
     "subnetAddressPrefix": { "value": "10.1.0.0/24" }
   }
   ```

2. Or check existing VNets:
   ```bash
   az network vnet list --query "[].{Name:name, Prefix:addressSpace.addressPrefixes}" -o table
   ```

### Issue: NSG rules blocking access

**Error Message:**
```
Unable to connect to session host. RDP connection failed.
```

**Solution:**
1. Verify NSG rules allow RDP:
   ```bash
   az network nsg rule list --resource-group <rg-name> --nsg-name <nsg-name> -o table
   ```

2. Add RDP rule if missing:
   ```bash
   az network nsg rule create --resource-group <rg-name> --nsg-name <nsg-name> --name AllowRdp --protocol Tcp --destination-port-range 3389 --access Allow --priority 100
   ```

---

## Session Host Issues

### Issue: Session hosts not registering with host pool

**Error Message:**
```
Session host status: Unavailable
```

**Solution:**
1. Check VM extension status:
   ```bash
   az vm extension list --resource-group <rg-name> --vm-name <vm-name> -o table
   ```

2. Verify AVD agent is installed:
   ```bash
   az vm run-command invoke --resource-group <rg-name> --vm-name <vm-name> --command-id RunPowerShellScript --scripts "Get-Service -Name RDAgent*"
   ```

3. Check registration token hasn't expired:
   ```bash
   az desktopvirtualization host-pool show --name <hp-name> --resource-group <rg-name> --query properties.registrationInfo
   ```

### Issue: Azure AD join failed

**Error Message:**
```
AAD join failed. Device is not joined to Azure AD.
```

**Solution:**
1. Verify AAD join extension status:
   ```bash
   az vm extension list --resource-group <rg-name> --vm-name <vm-name> --query "[?name=='AADLoginForWindows']"
   ```

2. Ensure your account has permission to join devices to Azure AD.

3. Check Azure AD device settings:
   - Go to Azure Portal → Azure Active Directory → Devices → Device settings
   - Ensure "Users may join devices to Azure AD" is set appropriately

### Issue: Session host stuck in "Unavailable" state

**Solution:**
1. Restart the VM:
   ```bash
   az vm restart --resource-group <rg-name> --name <vm-name>
   ```

2. If still unavailable, remove and re-add the session host:
   ```bash
   az desktopvirtualization session-host delete --host-pool-name <hp-name> --name <session-host-name> --resource-group <rg-name>
   ```

---

## PowerShell-Specific Issues

### Issue: PowerShell 7 not found

**Error Message:**
```
PowerShell 7.0 or higher is required
```

**Solution:**
Install PowerShell 7+:
```powershell
# Using winget
winget install Microsoft.PowerShell

# Using MSI
Invoke-WebRequest -Uri https://github.com/PowerShell/PowerShell/releases/download/v7.4.0/PowerShell-7.4.0-win-x64.msi -OutFile PowerShell.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I PowerShell.msi /quiet'
```

### Issue: Execution policy blocking script

**Error Message:**
```
cannot be loaded because running scripts is disabled on this system
```

**Solution:**
```powershell
# Check current execution policy
Get-ExecutionPolicy

# Set execution policy for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or bypass for single execution
powershell -ExecutionPolicy Bypass -File ./avd-lab.ps1 validate --config config/lab-dev.json
```

### Issue: Module not found

**Error Message:**
```
The term 'xxx' is not recognized as the name of a cmdlet
```

**Solution:**
Ensure required modules are installed:
```powershell
# Install Az module (if using Az cmdlets)
Install-Module -Name Az -Scope CurrentUser -Force

# Import module
Import-Module Az
```

### Issue: JSON parsing errors

**Error Message:**
```
ConvertFrom-Json : Invalid JSON primitive
```

**Solution:**
1. Validate your config file JSON:
   ```powershell
   Get-Content config/lab-dev.json | Test-Json
   ```

2. Check for trailing commas or missing quotes.

---

## Bash/Linux-Specific Issues

### Issue: Permission denied

**Error Message:**
```
bash: ./avd-lab.sh: Permission denied
```

**Solution:**
```bash
chmod +x avd-lab.sh
```

### Issue: jq not found

**Error Message:**
```
jq: command not found
```

**Solution:**
Install jq:
```bash
# Ubuntu/Debian
sudo apt-get install jq

# RHEL/CentOS
sudo dnf install jq

# macOS
brew install jq
```

### Issue: bc not found

**Error Message:**
```
bc: command not found
```

**Solution:**
Install bc:
```bash
# Ubuntu/Debian
sudo apt-get install bc

# RHEL/CentOS
sudo dnf install bc

# macOS
brew install bc
```

### Issue: Date format issues on macOS

**Error Message:**
```
date: illegal option -- d
```

**Solution:**
The script handles both GNU and BSD date. If issues persist, install GNU date:
```bash
brew install coreutils
# Then use gdate instead of date
```

---

## Cleanup and Orphaned Resources

### Issue: Orphaned resources after destroy

**Error Message:**
```
Found X orphaned resources
```

**Solution:**
1. List orphaned resources:
   ```bash
   az resource list --tag "lab-name=<lab-name>" -o table
   ```

2. Delete orphaned resources:
   ```bash
   az resource list --tag "lab-name=<lab-name>" --query "[].id" -o tsv | xargs -I {} az resource delete --ids {}
   ```

### Issue: Resource group stuck in deletion

**Solution:**
1. Check deletion status:
   ```bash
   az group show --name <rg-name> --query properties.provisioningState
   ```

2. Force delete if stuck:
   ```bash
   az group delete --name <rg-name> --yes --force-deletion-types Microsoft.Compute/virtualMachines
   ```

### Issue: Cannot delete due to locked resources

**Error Message:**
```
Scope 'xxx' cannot perform delete operation because following scope(s) are locked
```

**Solution:**
1. List locks:
   ```bash
   az lock list --resource-group <rg-name>
   ```

2. Delete locks:
   ```bash
   az lock delete --name <lock-name> --resource-group <rg-name>
   ```

---

## Getting Help

If you encounter an issue not covered in this guide:

1. **Check logs** in `logs/avd-lab/` directory
2. **Run with verbose output** by modifying the script to add `--verbose` flags
3. **Check Azure service health** for any ongoing issues
4. **Open an issue** with:
   - Full error message
   - Steps to reproduce
   - Azure CLI version (`az version`)
   - OS and shell version

## Useful Diagnostic Commands

```bash
# Check Azure CLI health
az doctor

# View deployment operations
az deployment operation group list --resource-group <rg-name> --name <deployment-name>

# View activity log
az monitor activity-log list --resource-group <rg-name> --caller $(az ad signed-in-user show --query userPrincipalName -o tsv)

# Check resource health
az resource health list --resource-group <rg-name>
```
