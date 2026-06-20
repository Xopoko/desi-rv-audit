#!/usr/bin/env bash
set -euo pipefail

MAIN_OUT="${1:-data/desi_main}"
CORRECTION_OUT="${2:-data/desi_corrections}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
elif [[ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
  PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"
else
  PYTHON="${PYTHON:-python}"
fi

"$PYTHON" -m desi_rv_audit.cli download-main \
  --main-output "$MAIN_OUT" \
  --correction-output "$CORRECTION_OUT"
