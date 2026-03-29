#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo "Missing .venv/bin/python. Run ./scripts/setup_cloud.sh first." >&2
  exit 1
fi

export PATH="$PWD/.venv/bin:$PATH"
exec .venv/bin/python scripts/run_pipeline.py "$@"
