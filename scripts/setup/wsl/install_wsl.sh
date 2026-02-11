#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
SKIP_AZ_LOGIN="${SKIP_AZ_LOGIN:-0}"

echo "=== Azure AI workshop WSL setup ==="
echo "Repo root: ${REPO_ROOT}"

if [[ $EUID -ne 0 ]]; then
  SUDO="sudo"
else
  SUDO=""
fi

echo "=== apt update ==="
${SUDO} apt-get update -y

echo "=== install base tools ==="
${SUDO} apt-get install -y \
  curl ca-certificates gnupg lsb-release software-properties-common \
  git python3 python3-venv python3-pip jq

if ! command -v az >/dev/null 2>&1; then
  echo "=== install Azure CLI ==="
  curl -sL https://aka.ms/InstallAzureCLIDeb | ${SUDO} bash
else
  echo "[OK] Azure CLI already installed"
fi

cd "${REPO_ROOT}"

echo "=== python virtualenv ==="
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  echo "[OK] created .venv"
else
  echo "[OK] .venv already exists"
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r labs/lab1-intake-assistant/requirements.txt
pip install -r labs/lab2-rag-policy-bot/requirements.txt

echo "=== az login check ==="
if ! az account show >/dev/null 2>&1; then
  if [[ "${SKIP_AZ_LOGIN}" == "1" ]]; then
    echo "[WARN] Not logged in to Azure yet (SKIP_AZ_LOGIN=1)."
  else
    echo "No active Azure login. Starting az login..."
    az login
  fi
else
  echo "[OK] Azure login active"
fi

echo ""
echo "Setup complete. Run verification:"
echo "  bash scripts/setup/wsl/verify_wsl.sh"
