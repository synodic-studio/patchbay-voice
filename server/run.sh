#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

UV_BIN="${UV_BIN:-}"
if [[ -z "$UV_BIN" ]]; then
    for candidate in "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv; do
        if [[ -x "$candidate" ]]; then UV_BIN="$candidate"; break; fi
    done
fi
if [[ -z "$UV_BIN" ]]; then UV_BIN="$(command -v uv 2>/dev/null || true)"; fi
if [[ -z "$UV_BIN" || ! -x "$UV_BIN" ]]; then
    echo "uv not found" >&2; sleep 30; exit 1
fi

exec "$UV_BIN" run uvicorn app:app --host "${VOICE_HOST:-127.0.0.1}" --port "${VOICE_PORT:-8800}"
