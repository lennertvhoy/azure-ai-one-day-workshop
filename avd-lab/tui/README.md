# AVD Lab TUI

A terminal user interface for managing Azure Virtual Desktop lab environments.

## Overview

The AVD Lab TUI provides a fast, safe, and intuitive interface for daily lab operations. It wraps the existing `avd-lab.sh` backend script with a user-friendly terminal UI.

## Features

- **Dashboard**: View all active labs in one screen with participant, lab-id, expiry, and status
- **Create Labs**: Guided wizard with validation and command preview
- **Destroy Labs**: Safe destruction with explicit confirmation (type "DELETE")
- **Validation**: Run prerequisite checks with structured results
- **Log Viewer**: View and search recent log files

## Requirements

- Python 3.11+
- [Textual](https://textual.textualize.io/) >= 0.47.0
- Azure CLI (`az`) installed and configured
- Existing `avd-lab.sh` backend script

## Installation

1. Navigate to the TUI directory:
   ```bash
   cd /home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/tui
   ```

2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the TUI application:

```bash
python app.py
```

Or with the virtual environment activated:

```bash
./app.py
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `c` | Create a new lab |
| `d` | Destroy selected lab |
| `v` | Run validation |
| `r` | Refresh lab list |
| `l` | View logs |
| `q` | Quit application |

## Screens

### Dashboard (Default)

The main screen shows a table of all active labs:

| Column | Description |
|--------|-------------|
| Lab ID | Unique identifier for the lab |
| Participant | Participant slug |
| Resource Group | Azure resource group |
| Region | Azure region |
| Expiry | Time until lab expires |
| Status | Running/Expired/Unknown |

### Create Lab Wizard

1. **Config Path**: Absolute path to configuration file (default prefilled)
2. **Participant Slug**: Required, validated (lowercase alphanumeric + hyphens)
3. **TTL**: Time-to-live (default 8h, options: 4h, 8h, 12h, 1d, 2d)

The wizard shows:
- Generated lab-id preview
- Command preview
- Validation warnings

### Destroy Confirmation

1. Shows lab metadata (lab-id, participant, resource group, expiry)
2. Displays explicit warning text
3. Requires typing "DELETE" to confirm
4. Shows the exact command being executed

### Validation View

Structured sections with color-coded indicators:
- **Green (✓)**: Check passed
- **Yellow (⚠)**: Warning
- **Red (✗)**: Error

Sections:
- Azure Authentication
- Azure Providers
- Quota Check
- Network Check
- Issues

### Log Viewer

- Select from recent log files
- Search/filter logs
- Color-coded log levels (ERROR, WARN, INFO, DEBUG)

## Architecture

```
tui/
├── app.py                    # Main application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── services/
│   ├── __init__.py
│   ├── cli_runner.py         # Safe subprocess wrapper
│   ├── parser.py             # Output parsing
│   └── state.py              # UI state management
├── widgets/
│   ├── __init__.py
│   ├── lab_table.py          # Lab table widget
│   ├── create_form.py        # Create lab form
│   ├── destroy_confirm.py    # Destroy confirmation dialog
│   ├── validation_view.py    # Validation results view
│   └── log_panel.py          # Log viewer panel
└── .state/
    └── ui-state.json         # Persistent UI state
```

## State Management

The TUI stores local state in `.state/ui-state.json`:

- Recent participants
- Last config path
- Last used TTL
- Recently selected lab IDs

**Note**: No secrets are stored.

## Safety Features

- No destructive action without explicit confirmation
- Destroy requires typing "DELETE" exactly
- All commands use absolute paths
- No shell string concatenation for user input
- Shows exact command before execution

## Backend Integration

The TUI wraps the existing `avd-lab.sh` script:

```bash
/home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/avd-lab.sh
```

Commands used:
- `validate --config <path>`
- `create --config <path> --participant <slug> --ttl <ttl>`
- `status --lab-id <id>` or `--participant <slug>`
- `destroy --lab-id <id> --yes`

## Troubleshooting

### "Backend script not found"

Ensure the `avd-lab.sh` script exists at the expected path and is executable:
```bash
chmod +x /home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/avd-lab.sh
```

### "Not logged in to Azure"

Run `az login` before using the TUI:
```bash
az login
```

### "Config file not found"

Ensure the config file path is absolute and the file exists:
```bash
ls -la /home/ff/.openclaw/workspace/repos/azure-ai-one-day-workshop/avd-lab/config/lab-dev.json
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Style

The codebase follows:
- PEP 8 style guidelines
- Type hints for all functions
- Docstrings for classes and public methods

## License

Part of the Azure AI One Day Workshop project.
