#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt yt-dlp
.venv/bin/python scripts/bootstrap_last30days.py

echo
echo "Cloud setup complete."
echo "Use this runner command:"
echo 'PATH="$PWD/.venv/bin:$PATH" .venv/bin/python scripts/run_pipeline.py'
