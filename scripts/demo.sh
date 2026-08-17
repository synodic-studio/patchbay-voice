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
# The screen shows artifacts, not narration. You do the talking. Three beats,
# each ending in a prompt that says what pressing the key means:
#
#   1. The invocation and the twelve tools, then a cue to ask from the phone.
#      The calls arrive underneath while it works.
#      "pi's own tools are off, so are extensions and skills. It reaches this
#       repo through twelve functions I wrote. Everything you are about to see
#       it do is one of them. write_file cannot leave docs/patchbay."
#      Press when the phone has finished speaking.
#
#   2. The branch, the note, the GitHub link.
#      "It answered out loud and left a document. Nothing was typed."
#
# Settings come from scripts/demo.env, which is gitignored; see
# scripts/demo.env.example. Without it the defaults target patchbay-go on a
# local server, on the branch the app already commits to.
#
# Before demoing on a machine for the first time:
#   1. The server is running and DEMO_PROJECT is checked out under ~/Developer.
#   2. In the app: pick that project, set the model, turn on auto-commit and
#      auto-push. DEMO_BRANCH matches the app's default, so leave it alone.
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
DEMO_BRANCH="${DEMO_BRANCH:-patchbay}"
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

beat() { printf '\n%s%s-- %s %s%s\n\n' "$D" "$B" "$1" "$(printf '%.0s-' $(seq 1 $((52 - ${#1}))))" "$R"; }
say()  { printf '%s%s%s\n' "$D" "$1" "$R"; }
warn() { printf '%s%s%s\n' "$Y" "$1" "$R"; }

# What you do, as opposed to what the machine is doing. Kept visually apart
# from everything else so it cannot be mistaken for output.
cue() {
  printf '\n%s%s   %s%s\n' "$Y" "$B" "$1" "$R"
  printf '%s%s   %s%s\n' "$Y" "$D" "$2" "$R"
}

# Every prompt says what pressing the key means, so there is never a question
# of whether it advances the slide or ends your turn.
advance() {
  [ -n "$AUTO" ] && return 0
  printf '\n%s   [ %s ]%s' "$D" "$1" "$R"
  read -n 1 -s -r _ </dev/tty 2>/dev/null || read -r _ </dev/tty 2>/dev/null
  printf '\r%*s\r' $((${#1} + 12)) ""
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
  # The server pushes fire-and-forget, so a push from the run being cleaned up
  # can land after the delete and put the branch straight back. Check twice.
  local pass
  for pass in 1 2; do
    if git -C "$PROJECT_DIR" ls-remote --exit-code --heads origin "$DEMO_BRANCH" >/dev/null 2>&1; then
      git -C "$PROJECT_DIR" push origin --delete "$DEMO_BRANCH"
    fi
    [ "$pass" = "1" ] && sleep 3
  done
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
  beat "how it reaches the repo"
  printf '%s  pi -p --mode json --provider litellm --model %s%s\n' "$C" "$DEMO_MODEL" "$R"
  printf '%s     %s--no-builtin-tools --no-extensions --no-skills%s\n' "$C" "$B" "$R"
  printf '%s     --extension pi/tools.ts%s\n\n' "$C" "$R"
  say "  pi's own tools, extensions, and skills are off. This is all it has."
  echo
  local tools
  tools=$(grep -oE 'name: "[a-z_]+"' "$ROOT/pi/tools.ts" | sed 's/name: "//;s/"//')
  printf '  %sread%s   %s\n' "$B" "$R" "$(echo "$tools" | sed -n '1,5p' | tr '\n' ' ')"
  printf '  %sgit%s    %s\n' "$B" "$R" "$(echo "$tools" | sed -n '6,11p' | tr '\n' ' ')"
  printf '  %swrite%s  %s   %s(%s only, enforced in the tool)%s\n' \
    "$B" "$R" "$(echo "$tools" | sed -n '12p')" "$D" "$DEMO_SAVE_PATH" "$R"
}

# Tool calls stream to the server log during the turn. Showing them turns
# the wait into the interesting part of the screen.
start_tail() {
  if [ ! -f "$DEMO_LOG" ]; then
    warn "No server log at $DEMO_LOG — set DEMO_LOG in scripts/demo.env."
    return
  fi
  # Stages, the transcript, the tool calls, and the reply, in the order the
  # server reaches them. The turn is otherwise a black box until it speaks.
  tail -n 0 -F "$DEMO_LOG" 2>/dev/null | awk -v g="$G" -v y="$Y" -v b="$B" -v d="$D" -v r="$R" '
    function wrap(s,   out, line, i, n, w) {
      n = split(s, w, " "); line = ""; out = ""
      for (i = 1; i <= n; i++) {
        if (length(line) + length(w[i]) + 1 > 68) { out = out "     " line "\n"; line = w[i] }
        else { line = (line == "" ? w[i] : line " " w[i]) }
      }
      return out "     " line
    }
    /\[pi:tool\]/      { sub(/^\[pi:tool\] [^ ]+ /, ""); print "     " g "->" r " " $0; fflush() }
    /\[turn:transcribing\]/ { print "\n  " d "transcribing what you said" r; fflush() }
    /\[turn:thinking\]/     { print "  " d "thinking" r; fflush() }
    /\[turn:speaking\]/     { print "\n  " d "synthesizing speech" r; fflush() }
    /\[turn:heard\]/   { sub(/^\[turn:heard\] [^ ]+ /, ""); print "\n  " y "you" r "\n" wrap($0) "\n"; fflush() }
    /\[turn:said\]/    { sub(/^\[turn:said\] [^ ]+ /, ""); print "\n  " b "it" r "\n" wrap($0); fflush() }
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
  beat "the branch it pushed"
  # The push is fire-and-forget so it never delays the spoken reply.
  local waited=0
  while [ $waited -lt 20 ]; do
    git -C "$PROJECT_DIR" ls-remote --exit-code --heads origin "$DEMO_BRANCH" >/dev/null 2>&1 && break
    sleep 1; waited=$((waited + 1))
  done

  printf '%s  $ git log --oneline -1 %s%s\n' "$C" "$DEMO_BRANCH" "$R"
  git -C "$PROJECT_DIR" log --oneline -1 "$DEMO_BRANCH" 2>/dev/null | sed 's/^/  /' \
    || warn "  no $DEMO_BRANCH branch yet"
  local note
  note=$(git -C "$PROJECT_DIR" show --pretty=format: --name-only "$DEMO_BRANCH" 2>/dev/null | grep -v '^$' | head -1)
  if [ -n "$note" ]; then
    printf '\n  %s%s%s\n' "$B" "$note" "$R"
    printf '  %shttps://github.com/%s/blob/%s/%s%s\n' "$D" "$DEMO_REPO" "$DEMO_BRANCH" "$note" "$R"
  else
    warn "  Nothing committed to $DEMO_BRANCH. Check auto-commit in the app."
  fi
}

beat_close() {
  beat "patchbay voice"
  printf '  iOS app, web client, same API. Server runs on brew, Docker, or a checkout.\n\n'
  printf '  %sgithub.com/synodic-studio/patchbay-voice%s\n' "$D" "$R"
}

# ---------------------------------------------------------------------------

[ -n "$CLEANUP" ] && { do_cleanup; exit 0; }

if [ ! -d "$PROJECT_DIR/.git" ]; then
  warn "No git repo at $PROJECT_DIR. Set DEMO_PROJECT in scripts/demo.env."
  exit 1
fi

VERSION=$(api GET "/api/version" | json "d['version']")
if [ -z "$VERSION" ]; then
  warn "No server at $HOST. Start it, or pass --host."
  exit 1
fi

# The payoff is a branch that did not exist a minute ago. If it is already
# there, the demo cannot show that, and --cleanup would delete whatever is on
# it. Refuse now rather than on the last slide.
if git -C "$PROJECT_DIR" rev-parse --verify "refs/heads/$DEMO_BRANCH" >/dev/null 2>&1 \
   || git -C "$PROJECT_DIR" ls-remote --exit-code --heads origin "$DEMO_BRANCH" >/dev/null 2>&1; then
  warn "$DEMO_PROJECT already has a $DEMO_BRANCH branch."
  warn "If it is left over from a previous run, clear it with --cleanup."
  warn "If it holds real notes, point DEMO_BRANCH somewhere else instead."
  exit 1
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

printf '\n  %sPatchbay Voice%s  %s%s · %s%s\n' "$B" "$R" "$D" "$DEMO_PROJECT" "$VERSION" "$R"

DRIVE_PID=""
if [ -n "$DRIVE" ]; then
  beat_harness
  start_tail
  drive_turn "$CHAT_ID" &
  DRIVE_PID=$!
  wait "$DRIVE_PID"
else
  # The tools go up before the question does, so the calls arrive underneath
  # the table that explains them, and the tail is already running when you
  # start talking.
  beat_harness
  cue "ON THE PHONE" "Pick $DEMO_PROJECT, hold the mic, and ask:"
  printf '\n%s' "$Y"
  printf '%s' "$DEMO_PROMPT" | fold -s -w 68 | sed 's/^/     /'
  printf '%s\n' "$R"
  start_tail
  advance "press when the phone has finished speaking"
fi
stop_tail

if [ -s "$REPLY_FILE" ]; then
  beat "what it said"
  python3 -c "import json;print(json.load(open('$REPLY_FILE'))['reply'])" 2>/dev/null \
    | fold -s -w 74 | sed 's/^/  /' || warn "no reply in response"
  advance "press for the branch"
fi

beat_result
advance "press to finish"
beat_close
echo
