#!/bin/bash
# Unified test runner for patchbay-voice. Runs every suite, aggregates the
# result, and fails if any suite fails. A missing toolchain (uv/node) is
# reported and skipped, not treated as a pass — install it to get coverage.
#
#   ./scripts/test.sh
#
# Wired into .githooks/pre-push. A fresh clone must re-point hooks with:
#   git config --local core.hooksPath .githooks
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
fail=0; skipped=""

run() {  # run <name> <cmd...>
    local name="$1"; shift
    echo "── $name ──────────────────────────────"
    if "$@"; then echo "✓ $name"; else echo "✗ $name FAILED"; fail=1; fi
    echo ""
}

# 1. brew CLI wrapper (bash, no toolchain needed)
run "brew wrapper" bash brew/tests/discover-urls.test.sh

# 2. server (pytest via uv)
if command -v uv &>/dev/null; then
    run "server" bash -c "cd server && uv run pytest -q"
else
    skipped+=" server(uv missing)"; echo "⊘ server SKIPPED — 'uv' not on PATH"; echo ""
fi

# 3. pi extension regression suite (node --test)
if command -v node &>/dev/null; then
    run "pi extension" node --test pi/tools.test.mts
else
    skipped+=" pi(node missing)"; echo "⊘ pi extension SKIPPED — 'node' not on PATH"; echo ""
fi

echo "════════════════════════════════════════"
[[ -n "$skipped" ]] && echo "skipped:$skipped"
if [[ $fail -eq 0 ]]; then echo "ALL SUITES PASSED"; else echo "TESTS FAILED"; fi
exit $fail
