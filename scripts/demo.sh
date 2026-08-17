#!/usr/bin/env bash
#
# A guided tour of a live turn, and a smoke test of a running server.
#
# The terminal is the slide deck. You ask the question from the phone; this
# shows what the agent is reaching for while it works, then what it left
# behind on a branch you can pull from a laptop.
#
#   --drive    ask the question from here instead of from the phone
#   --auto     run start to finish with no interaction, implies --drive
#   --host H   point at another server, default http://localhost:31552
#   --cleanup  delete the demo branch and note, then exit
#
# One keypress advances a beat. Settings come from scripts/demo.env, which is
# gitignored; see scripts/demo.env.example. Without it the defaults target
# patchbay-go on a local server.
#
# Before demoing on a machine for the first time:
#   1. The server is running and DEMO_PROJECT is checked out under ~/Developer.
#   2. In the app: pick that project, set the model, turn on auto-commit and
#      auto-push. The branch is whatever the app sends unless the server runs
#      with VOICE_FORCE_COMMIT_BRANCH=<DEMO_BRANCH>, which is the easier way.
#   3. Run it once with --auto, then --cleanup, so the first live run is not
#      the first run.
#
# Deliberately without `set -e`. A failed beat prints and the rest still runs.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="http://localhost:31552"
AUTO=""
DRIVE=""
CLEANUP=""

[ -f "$ROOT/scripts/demo.env" ] && . "$ROOT/scripts/demo.env"

DEMO_PROJECT="${DEMO_PROJECT:-patchbay-go}"
DEMO_REPO="${DEMO_REPO:-synodic-studio/patchbay-go}"
DEMO_BRANCH="${DEMO_BRANCH:-patchbay-demo}"
DEMO_MODEL="${DEMO_MODEL:-dsf}"
DEMO_SAVE_PATH="${DEMO_SAVE_PATH:-docs/patchbay/}"
DEMO_LOG="${DEMO_LOG:-$HOME/Library/Logs/patchbay-voice-server.log}"
DEMO_PROMPT="${DEMO_PROMPT:-Walk me through what happens when someone taps a Patchbay Go link, from the redirect through to the app opening, and save that as a note for a new contributor.}"
PROJECT_DIR="${DEVELOPER_DIR:-$HOME/Developer}/$DEMO_PROJECT"

while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="${2%/}"; shift 2 ;;
    --drive) DRIVE="1"; shift ;;
    --auto) AUTO="1"; DRIVE="1"; shift ;;
    --cleanup) CLEANUP="1"; shift ;;
    -h|--help) sed -n '3,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [ -t 1 ]; then
  B=$'\033[1m'; D=$'\033[2m'; C=$'\033[36m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[0m'
else
  B=""; D=""; C=""; G=""; Y=""; R=""
fi

beat() { printf '\n%s%s== %s%s\n\n' "$D" "$B" "$1" "$R"; }
say()  { printf '%s%s%s\n' "$D" "$1" "$R"; }
warn() { printf '%s%s%s\n' "$Y" "$1" "$R"; }

advance() {
  [ -n "$AUTO" ] && return 0
  printf '\n%s[any key]%s' "$D" "$R"
  read -n 1 -s -r _ </dev/tty 2>/dev/null || read -r _ </dev/tty 2>/dev/null
  printf '\r%*s\r' 12 ""
}

api() {  # api <method> <path> [curl args...]
  local method="$1" path="$2"; shift 2
  if [ -n "$VOICE_AUTH_TOKEN" ]; then
    curl -s -m 300 -X "$method" -H "Authorization: Bearer $VOICE_AUTH_TOKEN" "$HOST$path" "$@"
  else
    curl -s -m 300 -X "$method" "$HOST$path" "$@"
  fi
}

json() { python3 -c "import json,sys;d=json.load(sys.stdin);print($1)" 2>/dev/null; }

# ---------------------------------------------------------------------------

# Refuse to delete anything but the branch this demo creates. A typo in
# demo.env should not be able to reach a branch someone works on.
do_cleanup() {
  case "$DEMO_BRANCH" in
    main|master|develop|production|release|"")
      echo "refusing to clean up branch '$DEMO_BRANCH'" >&2; exit 2 ;;
  esac
  echo "Cleaning up $DEMO_PROJECT."
  if git -C "$PROJECT_DIR" rev-parse --verify "refs/heads/$DEMO_BRANCH" >/dev/null 2>&1; then
    git -C "$PROJECT_DIR" branch -D "$DEMO_BRANCH"
  fi
  if git -C "$PROJECT_DIR" ls-remote --exit-code --heads origin "$DEMO_BRANCH" >/dev/null 2>&1; then
    git -C "$PROJECT_DIR" push origin --delete "$DEMO_BRANCH"
  fi
  # The notes are real files on disk; the commit was built in a temp index.
  if [ -d "$PROJECT_DIR/$DEMO_SAVE_PATH" ]; then
    git -C "$PROJECT_DIR" ls-files --error-unmatch "$DEMO_SAVE_PATH" >/dev/null 2>&1 \
      || rm -rf "${PROJECT_DIR:?}/$DEMO_SAVE_PATH"
  fi
  local chat_id
  chat_id=$(resolve_chat)
  [ -n "$chat_id" ] && api POST "/api/chats/$chat_id/reset" >/dev/null && echo "chat reset"
  echo "Done."
}

# The chat the phone talks through, found by project so the script and the
# app always mean the same conversation.
resolve_chat() {
  api GET "/api/chats" | python3 -c "
import json,sys
try: body = json.load(sys.stdin)
except Exception: sys.exit(0)
chats = body.get('chats', []) if isinstance(body, dict) else body
for c in chats:
    if c.get('project_dir') == '$DEMO_PROJECT':
        print(c['id']); break
" 2>/dev/null
}

create_chat() {
  api POST "/api/chats" -H 'Content-Type: application/json' \
    -d "{\"name\":\"$DEMO_PROJECT\",\"project_dir\":\"$DEMO_PROJECT\"}" | json "d['id']"
}

# ---------------------------------------------------------------------------

beat_harness() {
  beat "What the agent is allowed to be"
  say "Every turn shells out to pi with the default harness switched off."
  echo
  printf '%s$ pi -p --mode json --provider litellm --model %s%s\n' "$C" "$DEMO_MODEL" "$R"
  printf '%s     %s--no-builtin-tools --no-extensions --no-skills%s\n' "$C" "$B" "$R"
  printf '%s     --extension pi/tools.ts%s\n' "$C" "$R"
  echo
  say "Those three flags drop pi's own tools, any globally installed"
  say "extension, and every skill on this machine. What is left is one file:"
  echo
  local tools
  tools=$(grep -oE 'name: "[a-z_]+"' "$ROOT/pi/tools.ts" | sed 's/name: "//;s/"//')
  printf '  %sread / search%s   %s\n' "$B" "$R" "$(echo "$tools" | sed -n '1,5p' | tr '\n' ' ')"
  printf '  %sgit history%s     %s\n' "$B" "$R" "$(echo "$tools" | sed -n '6,11p' | tr '\n' ' ')"
  printf '  %swrite%s           %s\n' "$B" "$R" "$(echo "$tools" | sed -n '12p')"
  echo
  say "Twelve functions. Every one takes explicit arguments and shells out"
  say "through an argv array, so a transcription that happens to contain"
  say "'&&' or '\$()' is inert. Reads are scoped to the project. write_file"
  say "is clamped to $DEMO_SAVE_PATH at the tool layer, not in the prompt."
  say "There is no shell tool, so there is no way out."
}

# Tool calls stream to the server log during the turn. Showing them turns
# the wait into the interesting part of the screen.
start_tail() {
  if [ ! -f "$DEMO_LOG" ]; then
    warn "No server log at $DEMO_LOG — set DEMO_LOG in scripts/demo.env."
    return
  fi
  printf '\n%s%s-- live from %s%s\n\n' "$D" "$B" "$DEMO_LOG" "$R"
  tail -n 0 -F "$DEMO_LOG" 2>/dev/null | awk -v g="$G" -v r="$R" '
    /\[pi:tool\]/ { sub(/^\[pi:tool\] [^ ]+ /, ""); print "  " g "->" r " " $0; fflush() }
  ' &
  TAIL_PID=$!
  # Detach it, or the shell prints "Terminated" over the next slide.
  disown "$TAIL_PID" 2>/dev/null
}

stop_tail() {
  [ -z "$TAIL_PID" ] && return
  kill "$TAIL_PID" 2>/dev/null
  pkill -f "tail -n 0 -F $DEMO_LOG" 2>/dev/null
  TAIL_PID=""
}

drive_turn() {
  local chat_id="$1"
  api POST "/api/talk" \
    -F "chat_id=$chat_id" \
    -F "text=$DEMO_PROMPT" \
    -F "model=$DEMO_MODEL" \
    -F "audio_response=false" \
    -F "save_path=$DEMO_SAVE_PATH" \
    -F "auto_commit=true" \
    -F "auto_commit_branch=$DEMO_BRANCH" \
    -F "auto_push=true" > "$REPLY_FILE"
}

beat_result() {
  beat "What it left behind"
  # The push is fire-and-forget so it never delays the spoken reply.
  local waited=0
  while [ $waited -lt 20 ]; do
    git -C "$PROJECT_DIR" ls-remote --exit-code --heads origin "$DEMO_BRANCH" >/dev/null 2>&1 && break
    sleep 1; waited=$((waited + 1))
  done

  printf '%s$ git log --oneline -1 %s%s\n' "$C" "$DEMO_BRANCH" "$R"
  git -C "$PROJECT_DIR" log --oneline -1 "$DEMO_BRANCH" 2>/dev/null || warn "no $DEMO_BRANCH branch yet"
  echo
  local note
  note=$(git -C "$PROJECT_DIR" show --pretty=format: --name-only "$DEMO_BRANCH" 2>/dev/null | grep -v '^$' | head -1)
  if [ -n "$note" ]; then
    printf '%s$ git show --name-only %s%s\n' "$C" "$DEMO_BRANCH" "$R"
    printf '  %s\n\n' "$note"
    say "Pushed, so it is already on GitHub:"
    printf '\n  %shttps://github.com/%s/blob/%s/%s%s\n' "$B" "$DEMO_REPO" "$DEMO_BRANCH" "$note" "$R"
    echo
    say "It answered out loud and left a document. Pick it up from a laptop,"
    say "or hand the branch to a cloud agent. Nothing was typed on a keyboard."
  else
    warn "Nothing committed to $DEMO_BRANCH. Check auto-commit in the app's settings."
  fi
}

beat_close() {
  beat "Patchbay Voice"
  say "iOS app and a single-file web client, same API. The server runs"
  say "wherever your code is: brew, Docker, or a checkout."
  echo
  printf '  %sgithub.com/synodic-studio/patchbay-voice%s\n' "$D" "$R"
}

# ---------------------------------------------------------------------------

[ -n "$CLEANUP" ] && { do_cleanup; exit 0; }

if [ ! -d "$PROJECT_DIR/.git" ]; then
  warn "No git repo at $PROJECT_DIR. Set DEMO_PROJECT in scripts/demo.env."
  exit 1
fi

VERSION_JSON=$(api GET "/api/version")
VERSION=$(printf '%s' "$VERSION_JSON" | json "d['version']")
if [ -z "$VERSION" ]; then
  warn "No server at $HOST. Start it, or pass --host."
  exit 1
fi

# A branch mismatch is invisible until the payoff slide, where it reads as the
# demo failing. Catch it here instead: either the server pins the branch, or
# the app's own branch field has to match.
FORCED_BRANCH=$(printf '%s' "$VERSION_JSON" | json "d.get('forced_commit_branch','')")
if [ "$FORCED_BRANCH" != "$DEMO_BRANCH" ]; then
  warn "Server is not pinning the commit branch to $DEMO_BRANCH."
  if [ -n "$FORCED_BRANCH" ]; then
    warn "It pins '$FORCED_BRANCH'. Set DEMO_BRANCH to match, or repin the server."
  else
    warn "Either set the app's branch field to $DEMO_BRANCH, or restart the"
    warn "server with VOICE_FORCE_COMMIT_BRANCH=$DEMO_BRANCH."
  fi
  echo
fi

CHAT_ID=$(resolve_chat)
[ -z "$CHAT_ID" ] && CHAT_ID=$(create_chat)
if [ -z "$CHAT_ID" ]; then
  warn "Could not find or create a chat for $DEMO_PROJECT."
  exit 1
fi

REPLY_FILE=$(mktemp)
TAIL_PID=""
trap 'stop_tail; rm -f "$REPLY_FILE"' EXIT

printf '\n%sPatchbay Voice%s  %s%s · %s · %s%s\n' "$B" "$R" "$D" "$HOST" "$VERSION" "$DEMO_PROJECT" "$R"

DRIVE_PID=""
if [ -n "$DRIVE" ]; then
  beat_harness
  start_tail
  drive_turn "$CHAT_ID" &
  DRIVE_PID=$!
  wait "$DRIVE_PID"
else
  # The tail starts before the question does, so the first tool call lands
  # while you are still holding the phone.
  beat "Ask it something"
  say "Hold the mic and ask. This is listening for what it reaches for."
  start_tail
  advance
  beat_harness
  advance
fi
stop_tail

if [ -s "$REPLY_FILE" ]; then
  beat "What it said"
  python3 -c "import json;print(json.load(open('$REPLY_FILE'))['reply'])" 2>/dev/null \
    || warn "no reply in response"
  advance
fi

beat_result
advance
beat_close
echo
