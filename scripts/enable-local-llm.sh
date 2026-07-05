#!/bin/bash
# enable-local-llm.sh — opt-in: run pi against a local Gemma model via Ollama,
# so Patchbay Voice needs NO cloud LLM credentials.
#
# This is deliberately NOT part of the default install (the base server stays
# minimal-deps). Run it explicitly when you want fully-local operation:
#
#     scripts/enable-local-llm.sh                 # default model (gemma4:e2b)
#     scripts/enable-local-llm.sh gemma4:e4b      # pick a bigger model
#
# Gemma 4 supports tool-calling, so write_file works offline. (Gemma 3 does not
# — it is conversational-only.) gemma4:e2b is ~7.2GB, so this is opt-in by design.
#
# Undo with: scripts/enable-local-llm.sh --disable
set -euo pipefail

MODEL="${1:-gemma4:e2b}"
OLLAMA_URL="http://localhost:11434/v1"
PI_AGENT_DIR="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
PLIST="$HOME/Library/LaunchAgents/com.synodic.patchbay-voice-server.plist"
SERVICE="com.synodic.patchbay-voice-server"

log() { printf '\033[1;36m==>\033[0m %s\n' "$1"; }

_set_server_env() {
    # Wire PI_PROVIDER/PI_MODEL into whichever deployment is active.
    local provider="$1" model="$2"
    if [[ -f "$PLIST" ]]; then
        /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PI_PROVIDER string $provider" "$PLIST" 2>/dev/null \
            || /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PI_PROVIDER $provider" "$PLIST"
        /usr/libexec/PlistBuddy -c "Add :EnvironmentVariables:PI_MODEL string $model" "$PLIST" 2>/dev/null \
            || /usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:PI_MODEL $model" "$PLIST"
        log "Set PI_PROVIDER=$provider PI_MODEL=$model in $PLIST"
        launchctl bootout "gui/$(id -u)/$SERVICE" 2>/dev/null || true
        launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || true
        log "Reloaded the launchd service"
    else
        # Brew-service deployment: launchctl setenv + restart.
        launchctl setenv PI_PROVIDER "$provider"
        launchctl setenv PI_MODEL "$model"
        brew services restart patchbay-voice-server 2>/dev/null || true
        log "Set env via launchctl setenv and restarted the brew service"
    fi
}

if [[ "${1:-}" == "--disable" ]]; then
    log "Reverting server to the default cloud provider (litellm)"
    if [[ -f "$PLIST" ]]; then
        /usr/libexec/PlistBuddy -c "Delete :EnvironmentVariables:PI_PROVIDER" "$PLIST" 2>/dev/null || true
        /usr/libexec/PlistBuddy -c "Delete :EnvironmentVariables:PI_MODEL" "$PLIST" 2>/dev/null || true
        launchctl bootout "gui/$(id -u)/$SERVICE" 2>/dev/null || true
        launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || true
    else
        launchctl unsetenv PI_PROVIDER; launchctl unsetenv PI_MODEL
        brew services restart patchbay-voice-server 2>/dev/null || true
    fi
    log "Local LLM disabled. (The Ollama model and pi provider config are left in place.)"
    exit 0
fi

# 1. Ensure Ollama is installed and running.
if ! command -v ollama >/dev/null 2>&1; then
    log "Installing Ollama via Homebrew"
    brew install ollama
fi
if ! curl -sf "$OLLAMA_URL/../api/version" >/dev/null 2>&1; then
    log "Starting Ollama service"
    brew services start ollama 2>/dev/null || (ollama serve >/dev/null 2>&1 &)
    for i in $(seq 1 15); do curl -sf "$OLLAMA_URL/../api/version" >/dev/null 2>&1 && break; sleep 1; done
fi

# 2. Pull the model.
log "Pulling $MODEL (this can be several GB)"
ollama pull "$MODEL"

# 3. Add an 'ollama' provider to pi's models.json (non-destructive).
log "Registering the ollama provider in $PI_AGENT_DIR/models.json"
mkdir -p "$PI_AGENT_DIR"
MODEL="$MODEL" OLLAMA_URL="$OLLAMA_URL" python3 - "$PI_AGENT_DIR/models.json" <<'PY'
import json, os, sys
p = sys.argv[1]
model = os.environ["MODEL"]
d = json.load(open(p)) if os.path.exists(p) else {}
d.setdefault("providers", {})
prov = d["providers"].get("ollama", {
    "baseUrl": os.environ["OLLAMA_URL"],
    "api": "openai-completions",
    "apiKey": "ollama",  # Ollama ignores it; OpenAI clients require non-empty
    "compat": {"supportsDeveloperRole": False, "supportsUsageInStreaming": False},
    "models": [],
})
prov["baseUrl"] = os.environ["OLLAMA_URL"]
if not any(m.get("id") == model for m in prov["models"]):
    prov["models"].append({
        "id": model,
        "name": f"{model} (local)",
        "reasoning": False,
        "input": ["text"],
        "contextWindow": 128000,
        "maxTokens": 8192,
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
    })
d["providers"]["ollama"] = prov
json.dump(d, open(p, "w"), indent=1)
print(f"  ollama provider models: {[m['id'] for m in prov['models']]}")
PY

# 4. Point the server at it and restart.
_set_server_env "ollama" "$MODEL"

cat <<EOF

Local LLM enabled — Patchbay Voice now runs pi on $MODEL via Ollama, no cloud key needed.

Notes:
  * The iOS model picker (Small/Medium/Large) still names cloud aliases; in local
    mode leave the server default in charge or wire the app to send "$MODEL".
  * Small Gemma is a weaker coding agent than a frontier cloud model — expect
    simpler edits. It DOES support the write_file tool.
  * Revert with: scripts/enable-local-llm.sh --disable
EOF
