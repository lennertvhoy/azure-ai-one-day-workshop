# AVD Lab Lifecycle Tool

A safe, repeatable tool to provision and tear down Azure Virtual Desktop (AVD) environments for course testing, with minimal manual steps and clear cost controls.

## Features

- **Create** - Spin up a fresh AVD lab environment for testing course steps
- **Destroy** - Tear down the full environment cleanly after tests to avoid cost drift
- **Status** - Check the current state of your AVD lab
- **Validate** - Verify prerequisites before deployment
- **Estimate Cost** - Get rough daily/hourly cost estimates
- **Collision-Free Naming** - Unique lab IDs prevent parallel lab conflicts

## Quick Start

### Prerequisites

1. **Azure CLI** installed and authenticated
   ```bash
   # Install Azure CLI (if not already installed)
   # See: https://docs.microsoft.com/cli/azure/install-azure-cli
   
   # Login to Azure
   az login
   ```

2. **Bicep** (installed automatically via Azure CLI)

3. **PowerShell 7+** (for PowerShell wrapper) or **Bash** (for Bash wrapper)

### Installation

Clone or copy the `avd-lab` directory to your local machine:

```bash
cd avd-lab
```

### Basic Usage

#### 1. Validate Prerequisites

```bash
# PowerShell
./avd-lab.ps1 validate --config config/lab-dev.json

# Bash
./avd-lab.sh validate --config config/lab-dev.json
```

This checks:
- Azure CLI installed and logged in
- Correct subscription selected
- Required providers registered
- Quota availability for selected VM size/region
- Network/address space collisions

#### 2. Create an AVD Lab

```bash
# PowerShell
./avd-lab.ps1 create --config config/lab-dev.json --participant lenny --ttl 8h

# Bash
./avd-lab.sh create --config config/lab-dev.json --participant lenny --ttl 8h
```

This will:
- Generate a unique lab-id (e.g., `azure-lenny-202602120938-a7k2`)
- Create a resource group with the lab-id as name
- Deploy network components (VNet, Subnet, NSG)
- Create AVD Host Pool, Workspace, and Desktop Application Group
- Deploy session host VMs with AVD agent
- Tag all resources with lab-id, participant, and expiry time

#### 3. Check Lab Status

```bash
# By participant
./avd-lab.sh status --participant lenny

# By lab-id
./avd-lab.sh status --lab-id azure-lenny-202602120938-a7k2
```

#### 4. Estimate Costs

```bash
./avd-lab.sh estimate-cost --config config/lab-dev.json --hours 8
```

#### 5. Destroy the Lab

```bash
# By participant
./avd-lab.sh destroy --participant lenny --yes

# By lab-id
./avd-lab.sh destroy --lab-id azure-lenny-202602120938-a7k2 --yes
```

## Lab ID Format

Lab IDs are auto-generated to ensure uniqueness and prevent collisions:

```
<course>-<participant>-<YYYYMMDDHHmm>-<rand4>
```

Example: `azure-lenny-202602120938-a7k2`

- **course**: From config tags.course (sanitized to lowercase alphanumeric)
- **participant**: Required `--participant` slug
- **timestamp**: Creation time (YYYYMMDDHHmm)
- **rand4**: 4-character random suffix for uniqueness

## Collision Prevention

The tool prevents naming collisions between parallel labs:

1. **Unique Lab IDs**: Auto-generated with timestamp and random suffix
2. **Participant Check**: Preflight check fails if participant already has an active (non-expired) lab
3. **Lab-ID Check**: Preflight check ensures lab-id doesn't already exist
4. **Tag-based Targeting**: Destroy targets by lab-id or participant, not ambiguous names

## Configuration

### Configuration File Structure

The tool uses JSON configuration files in `config/` directory:

```json
{
  "parameters": {
    "subscriptionId": { "value": "${AZ_SUBSCRIPTION_ID}" },
    "location": { "value": "${AZ_LOCATION:-westeurope}" },
    "vmSize": { "value": "Standard_D2s_v3" },
    "vmImage": {
      "value": {
        "publisher": "MicrosoftWindowsDesktop",
        "offer": "windows-11",
        "sku": "win11-23h2-pro",
        "version": "latest"
      }
    },
    "hostPoolType": { "value": "Pooled" },
    "loadBalancerType": { "value": "BreadthFirst" },
    "maxSessionsPerHost": { "value": 10 },
    "numberOfSessionHosts": { "value": 2 },
    "vnetAddressPrefix": { "value": "10.0.0.0/16" },
    "subnetAddressPrefix": { "value": "10.0.0.0/24" },
    "aadJoinType": { "value": "AzureAD" },
    "tags": {
      "value": {
        "managed-by": "avd-lab-tool",
        "owner": "${OWNER:-lab-admin}",
        "course": "${COURSE:-azure-ai-workshop}",
        "costCenter": "${COST_CENTER:-training}"
      }
    }
  }
}
```

### Environment Variables

Override configuration values with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AZ_SUBSCRIPTION_ID` | Azure subscription ID | (required) |
| `AZ_LOCATION` | Azure region | `westeurope` |
| `OWNER` | Owner tag value | `lab-admin` |
| `COURSE` | Course tag value (used in lab-id) | `azure-ai-workshop` |
| `COST_CENTER` | Cost center tag value | `training` |

### VM Size Options

Common VM sizes for AVD session hosts:

| Size | vCPUs | RAM | Est. Hourly Cost |
|------|-------|-----|------------------|
| Standard_D2s_v3 | 2 | 8GB | ~$0.10 |
| Standard_D4s_v3 | 4 | 16GB | ~$0.20 |
| Standard_D8s_v3 | 8 | 32GB | ~$0.40 |
| Standard_D2s_v5 | 2 | 8GB | ~$0.12 |
| Standard_D4s_v5 | 4 | 16GB | ~$0.24 |

## CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `validate` | Validate prerequisites and configuration |
| `create` | Create a new AVD lab environment |
| `destroy` | Destroy an AVD lab environment |
| `status` | Show status of an AVD lab environment |
| `estimate-cost` | Estimate cost for running a lab |
| `help` | Show help message |

### Options

| Option | Description |
|--------|-------------|
| `--config <path>` | Path to configuration file |
| `--participant <slug>` | Participant slug (required for create) |
| `--lab-id <id>` | Lab ID (for destroy/status) |
| `--name <id>` | Alias for --lab-id |
| `--ttl <duration>` | Time-to-live (e.g., `8h`, `1d`) |
| `--hours <number>` | Hours for cost estimation |
| `--yes` | Skip confirmation prompts |
| `--dry-run` | Show what would be done without making changes |

### Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Validation/config error |
| 2 | Azure API/deploy failure |
| 3 | Safety check blocked action |

## Safety Controls

The tool includes several safety mechanisms:

1. **Explicit Confirmation** - `destroy` requires `--yes` flag or interactive confirmation
2. **Tag-based Management** - Only resources tagged with `managed-by=avd-lab-tool` can be destroyed
3. **Collision Prevention** - Preflight checks prevent duplicate labs for same participant
4. **Expiry Tags** - All resources tagged with expiry time for cleanup automation
5. **Fail-Fast Validation** - `create` fails fast on missing prerequisites

## Resource Tagging

All created resources are tagged with:

| Tag | Description | Example |
|-----|-------------|---------|
| `managed-by` | Tool identifier | `avd-lab-tool` |
| `lab-id` | Unique lab identifier | `azure-lenny-202602120938-a7k2` |
| `participant` | Participant slug | `lenny` |
| `expiry` | Expiration timestamp | `2026-02-12T17:00:00Z` |
| `owner` | Owner identifier | `lab-admin` |
| `course` | Course identifier | `azure-ai-workshop` |
| `costCenter` | Cost center | `training` |

## Architecture

```
avd-lab/
├── config/
│   └── lab-dev.json          # Sample configuration
├── iac/
│   ├── main.bicep            # Main Bicep template
│   └── modules/
│       ├── network.bicep     # VNet, Subnet, NSG
│       ├── hostpool.bicep    # AVD Host Pool
│       ├── workspace.bicep   # AVD Workspace
│       ├── appgroup.bicep    # Desktop Application Group
│       └── sessionhosts.bicep # Session Host VMs
├── logs/
│   └── avd-lab/              # Structured logs
├── avd-lab.ps1               # PowerShell CLI
├── avd-lab.sh                # Bash CLI
└── README.md                 # This file
```

## Logging

All operations are logged to `logs/avd-lab/` with:
- JSON structured logs for machine parsing
- Human-readable console output
- Timestamps in ISO 8601 format

Log file naming: `YYYYMMDD-HHMMSS.log`

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and solutions.

## Examples

### Full Workflow

```bash
# 1. Set environment variables
export AZ_SUBSCRIPTION_ID="your-subscription-id"
export AZ_LOCATION="westeurope"
export OWNER="your-name"

# 2. Validate
./avd-lab.sh validate --config config/lab-dev.json

# 3. Create lab (generates unique lab-id)
./avd-lab.sh create --config config/lab-dev.json --participant lenny --ttl 8h

# 4. Check status
./avd-lab.sh status --participant lenny

# 5. After testing, destroy
./avd-lab.sh destroy --participant lenny --yes
```

### Parallel Labs (No Collision)

```bash
# Participant 1
./avd-lab.sh create --config config/lab-dev.json --participant alice --ttl 8h
# Creates: azure-alice-202602120938-a7k2

# Participant 2 (can run in parallel)
./avd-lab.sh create --config config/lab-dev.json --participant bob --ttl 8h
# Creates: azure-bob-202602120940-x9m3

# Each participant can manage their own lab
./avd-lab.sh status --participant alice
./avd-lab.sh status --participant bob

# Destroy individually
./avd-lab.sh destroy --participant alice --yes
./avd-lab.sh destroy --participant bob --yes
```

### Dry Run

Preview what would be created without actually deploying:

```bash
./avd-lab.sh create --config config/lab-dev.json --participant test-user --dry-run
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, please open an issue in the repository.
