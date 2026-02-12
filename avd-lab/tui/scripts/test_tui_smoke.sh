#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================"
echo "AVD TUI Smoke Test Harness"
echo "========================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TUI_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$TUI_DIR/.venv_smoke"

# 1. Environment Setup
echo -e "\n[1/4] Setting up test environment..."
if [ -d "$VENV_DIR" ]; then
    echo "Removing existing smoke test venv..."
    rm -rf "$VENV_DIR"
fi

echo "Creating new venv at $VENV_DIR..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 2. Install Dependencies
echo -e "\n[2/4] Installing dependencies..."
pip install -U pip > /dev/null
if pip install -r "$TUI_DIR/requirements.txt" > /dev/null; then
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}✗ Dependency installation failed${NC}"
    exit 1
fi

# Verify strict versioning
if ! pip freeze | grep -q "textual==0.70.0"; then
    echo -e "${RED}✗ Textual version mismatch. Expected 0.70.0${NC}"
    pip freeze | grep textual
    exit 1
fi

# Install test dependencies (if any extra are needed, typically textual-dev)
# For now we assume they are in requirements or we install them here
if ! pip freeze | grep -q "pytest"; then
    echo "Installing pytest..."
    pip install pytest pytest-asyncio > /dev/null
fi

# 3. Static Analysis / Import Check
echo -e "\n[3/4] Verify Imports..."
export PYTHONPATH="$TUI_DIR"
if python3 -c "import app; import widgets.create_form; import services.parser; print('Imports succesful')" > /dev/null; then
     echo -e "${GREEN}✓ Core modules import cleanly${NC}"
else
     echo -e "${RED}✗ Import check failed${NC}"
     exit 1
fi

# 4. Run Test Suite
echo -e "\n[4/4] Running Smoke Tests..."
cd "$TUI_DIR"
if pytest tests/ -v; then
    echo -e "\n${GREEN}========================================"
    echo "PASS: AVD TUI Smoke Tests"
    echo "========================================${NC}"
    exit 0
else
    echo -e "\n${RED}========================================"
    echo "FAIL: Smoke tests failed"
    echo "========================================${NC}"
    exit 1
fi
