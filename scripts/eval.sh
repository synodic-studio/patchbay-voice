#!/bin/bash
# Explicit live model calls; normal tests remain offline.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/server"
exec uv run python eval_runner.py "$@"
