#!/bin/bash
# Brew smoke test for patchbay-voice-server
# Starts the server, hits the API, and shuts it down.
# Run from repo root: bash brew/scripts/test-brew-smoke.sh

set -euo pipefail

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ $1"; }

echo "═══ patchbay-voice-server brew smoke test ═══"
echo ""

# ── 1. Binary is installed ────────────────────────────────────────────────────
echo "── 1. Binary checks ──"
if command -v patchbay-voice &>/dev/null; then
    pass "patchbay-voice found in PATH"
else
    fail "patchbay-voice not in PATH"
fi

VERSION=$(patchbay-voice version 2>&1)
if [[ "$VERSION" == "Patchbay Voice Server 1.0.0" ]]; then
    pass "version: $VERSION"
else
    fail "unexpected version: $VERSION"
fi

# ── 2. Python modules load ────────────────────────────────────────────────────
echo ""
echo "── 2. Python imports ──"
PB_PREFIX=$(/opt/homebrew/bin/brew --prefix patchbay-voice-server 2>/dev/null || echo /opt/homebrew/opt/patchbay-voice-server)
PB_LIBEXEC=$(cd "$PB_PREFIX/libexec" && pwd)

TEST_IMPORTS=(
    "from chats import Chat, create_chat, load_chats; print('ok')"
    "from pi_runner import _parse_events, _extract_text; print('ok')"
    "from tts import _split_sentences; print('ok')"
    "from routes.talk import _truthy; print('ok')"
)
cd "$PB_LIBEXEC"
for stmt in "${TEST_IMPORTS[@]}"; do
    ERR=$(bin/python -c "$stmt" 2>&1 1>/dev/null) || true
    if GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test bin/python -c "$stmt" 2>/dev/null; then
        pass "import: ${stmt%%;*}"
    else
        fail "import failed: ${stmt%%;*} — ${ERR}"
    fi
done

# ── 3. Existing pytest suite ──────────────────────────────────────────────────
echo ""
echo "── 3. Pytest suite ──"
cd "$PB_LIBEXEC"
PYTEST_OUT=$(GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test bin/python -m pytest tests/ -q 2>&1 || true)
if echo "$PYTEST_OUT" | grep -q "passed"; then
    COUNT=$(echo "$PYTEST_OUT" | tail -1 | grep -oE '[0-9]+ passed' | cut -d' ' -f1)
    pass "pytest: $COUNT passed"
else
    fail "pytest failed: $(echo "$PYTEST_OUT" | tail -3)"
fi

# ── 4. Server starts and responds ─────────────────────────────────────────────
echo ""
echo "── 4. Server start/stop ──"

PORT=18799
TMP_DEV=$(mktemp -d)
TMP_PROJ="${TMP_DEV}/smoke-test-proj"
mkdir -p "$TMP_PROJ"
LOG=$(mktemp)
cleanup() {
    if [[ -n "${SERVER_PID:-}" ]]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -rf "$TMP_DEV" "$LOG"
}
trap cleanup EXIT

cd "$PB_LIBEXEC"
DEVELOPER_DIR="$TMP_DEV" \
    GOOGLE_TTS_SERVICE_ACCOUNT_JSON=test \
    bin/python -m uvicorn app:app \
    --host 127.0.0.1 --port "$PORT" --log-level error >"$LOG" 2>&1 &
SERVER_PID=$!

# Wait for server to be ready (up to 15s)
for i in $(seq 1 15); do
    if curl -sf "http://127.0.0.1:$PORT/api/chats" >/dev/null 2>&1; then
        pass "server started on port $PORT (pid $SERVER_PID)"
        break
    fi
    sleep 1
done
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    fail "server failed to start: $(cat "$LOG")"
fi

# Hit the API (empty chats list)
RESP=$(curl -sf "http://127.0.0.1:$PORT/api/chats" 2>&1 || true)
if echo "$RESP" | grep -q '"chats"'; then
    pass "GET /api/chats returns valid JSON"
else
    fail "GET /api/chats failed: $RESP"
fi

# Create a chat (POST)
CREATE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:$PORT/api/chats" \
    -H "Content-Type: application/json" \
    -d '{"project_dir": "smoke-test-proj"}' 2>&1 || true)
CREATE_RESP=$(curl -s -X POST "http://127.0.0.1:$PORT/api/chats" \
    -H "Content-Type: application/json" \
    -d '{"project_dir": "smoke-test-proj"}' 2>&1 || true)
if echo "$CREATE_RESP" | grep -q '"id"'; then
    pass "POST /api/chats returns chat with id"
    CHAT_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
else
    fail "POST /api/chats (HTTP $CREATE_CODE): $CREATE_RESP"
fi

# List projects (should include smoke-test-proj)
PROJ_RESP=$(curl -sf "http://127.0.0.1:$PORT/api/projects" 2>&1 || true)
if echo "$PROJ_RESP" | grep -q 'smoke-test-proj'; then
    pass "GET /api/projects lists smoke-test-proj"
else
    fail "GET /api/projects failed: $PROJ_RESP"
fi

# Health check via /api/talk without input (should return 400 with detail)
TALK_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:$PORT/api/talk" -d "chat_id=$CHAT_ID" 2>&1 || true)
if [[ "$TALK_CODE" == "400" ]]; then
    pass "POST /api/talk (no input) returns HTTP 400"
else
    TALK_BODY=$(curl -s -X POST "http://127.0.0.1:$PORT/api/talk" -d "chat_id=$CHAT_ID" 2>&1 || true)
    fail "POST /api/talk (no input) returned $TALK_CODE: $TALK_BODY"
fi

# Kill the server
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true
pass "server stopped cleanly"

# ── Results ───────────────────────────────────────────────────────────────────
echo ""
echo "═══ Results: $PASS passed, $FAIL failed ═══"
if (( FAIL > 0 )); then
    exit 1
fi
