#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
FAILS=0

ok(){ echo "[OK] $1"; }
fail(){ echo "[FAIL] $1"; FAILS=$((FAILS+1)); }

echo "Verifying WSL environment"
echo "Repo: ${REPO_ROOT}"

command -v git >/dev/null 2>&1 && ok "Git available" || fail "Git missing"

if command -v python3 >/dev/null 2>&1; then
  PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  MAJOR=${PYV%%.*}; MINOR=${PYV##*.}
  if [[ "$MAJOR" -gt 3 || ("$MAJOR" -eq 3 && "$MINOR" -ge 11) ]]; then
    ok "Python ${PYV} (>=3.11)"
  else
    fail "Python 3.11+ required, found ${PYV}"
  fi
else
  fail "Python3 missing"
fi

command -v az >/dev/null 2>&1 && ok "Azure CLI available" || fail "Azure CLI missing"

if az account show >/dev/null 2>&1; then
  ok "Azure login active"
else
  fail "Azure login missing (run az login)"
fi

[[ -f "${REPO_ROOT}/labs/lab1-intake-assistant/requirements.txt" ]] && ok "Lab1 requirements present" || fail "Missing Lab1 requirements"
[[ -f "${REPO_ROOT}/labs/lab2-rag-policy-bot/requirements.txt" ]] && ok "Lab2 requirements present" || fail "Missing Lab2 requirements"

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  if "${REPO_ROOT}/.venv/bin/python" -c 'import fastapi,uvicorn,pydantic,dotenv,openai,azure.search.documents' >/dev/null 2>&1; then
    ok "Python package imports via .venv"
  else
    fail "Package imports failed in .venv"
  fi
else
  if python3 -c 'import fastapi,uvicorn,pydantic,dotenv,openai,azure.search.documents' >/dev/null 2>&1; then
    ok "Python package imports (global)"
  else
    fail "Package imports failed"
  fi
fi

if ss -ltn '( sport = :8000 )' | grep -q LISTEN; then
  fail "Port 8000 already in use"
else
  ok "Port 8000 free"
fi

echo
if [[ "$FAILS" -eq 0 ]]; then
  echo "Environment verification PASSED ✅"
  exit 0
else
  echo "Environment verification has ${FAILS} failure(s)."
  exit 1
fi
