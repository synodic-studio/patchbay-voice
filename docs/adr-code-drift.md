# ADR / code drift audit

Verifies each ADR's concrete claims against the implementing code. Every verdict
cites file:line. CONFIRMED = code matches; DRIFTED = code contradicts or omits;
UNVERIFIABLE = no code path found.

## Summary

| ADR | Status |
|-----|--------|
| 0001 tts-fallback-chain | CONFIRMED |
| 0002 turn-submission-queue | **DRIFTED** (no durable queue; a per-chat lock holding the HTTP request open) |
| 0003 failed-turn-persistence-and-audio | **DRIFTED → RESOLVED** by ADR 0009 (client now speaks `spoken_notice`) |
| 0004 single-chat-per-project | CONFIRMED |
| 0005 audio-lifetime | CONFIRMED (in-memory tracking lost on restart) |
| 0006 on-device-speech | CONFIRMED (see 0003 for the failed-turn silence) |
| 0007 server-authoritative-turns | CONFIRMED |
| 0008 tools-read-and-note-not-edit | CONFIRMED (undocumented: server auto-commits/pushes notes) |

---

## 0002 turn-submission-queue - DRIFTED

The ADR title is "Submitting during an in-progress turn queues, never blocks or
drops," and the body says every submission is "accepted immediately and processed
as an independent turn in strict FIFO order," explicitly replacing "the server's
per-chat lock, which previously just made the caller wait."

- DRIFTED - there is no server-side queue. The mechanism is a per-chat
  `asyncio.Lock` (`server/routes/talk.py:31`) acquired inside the `/api/talk`
  handler at `server/routes/talk.py:81` (`async with _talk_locks[chat_id]:`), and
  the entire turn (ASR, `run_pi`, TTS) runs inside that block. The client's HTTP
  request is held open for the whole turn. The "queue" exists only as blocked
  in-flight HTTP requests: it is lost on server restart and on any client timeout,
  and a dropped connection drops the waiting submission. The ADR claims to replace
  "the per-chat lock which just made the caller wait," but the code *is* exactly
  that lock. So "never blocks" is false (the caller blocks for the whole turn) and
  "never drops" is false (restart/timeout lose the waiter).
- FIFO sub-claim, partially CONFIRMED but weaker than stated: CPython's
  `asyncio.Lock` does wake waiters in FIFO order (the comment at
  `talk.py:24-30` is accurate), so lock acquisition is fair. But the iOS client
  fires submissions as independent concurrent requests (`inFlightCount` can exceed
  1; `TalkViewModel.swift:114-145`), so arrival order at the server is not
  guaranteed to equal the user's submission order. "Strict FIFO" holds only for
  lock-acquisition order, not end-to-end submission order.
- CONFIRMED (no merging): each turn is one independent `run_pi` call
  (`talk.py:166`); no code combines queued turns.
- CONFIRMED (client-side `pendingText` removed): no `pendingText` remains in
  `ios/`; each submission spawns its own task (`TalkViewModel.swift:114`, `:129`).

## 0003 failed-turn-persistence-and-audio - DRIFTED → RESOLVED

**Resolved** by [ADR 0009](adr/0009-client-speaks-failure-notice.md): the server now
always returns the notice text as `spoken_notice` on a Failed turn (`talk.py`
`_failed_response`), and the client speaks it on-device when the server sent no
audio, via the pure `TalkViewModel.playback(for:onDevice:)` decision
(`TalkViewModel+Audio.swift`), regression-tested in `PatchbayVoiceTests.swift`
(`TalkViewModelPlaybackTests`) and `test_routes.py`
(`test_failed_turn_carries_spoken_notice_without_server_audio`). The original
finding, kept for the record:

- DRIFTED - the failed-turn generic notice is silent in on-device TTS mode,
  breaking the ADR's concrete claim that the notice "gets synthesized and spoken"
  and its rationale that "silence on failure would leave them waiting
  indefinitely." Full chain: in on-device mode the client sends
  `audio_response=false` (`ServerClient.swift:132-133`); the server then sets
  `want_audio = False` (`talk.py:87`); the failed-turn notice synthesis is gated on
  `want_audio` (`talk.py:155-157` into `_synthesize_audio`, whose body only
  synthesizes `if want_audio and text` at `talk.py:245`), so no notice audio is
  produced; the client excludes failed turns from on-device speech
  (`TalkViewModel+Audio.swift:13`, `!response.failed`) and then returns on empty
  paths (`:19`). Net result: a failed turn in on-device mode plays nothing. This is
  reachable in the normal on-device provider mode (`ttsProvider == "ondevice"`,
  `TurnSettings.swift:20,31`), not only the demo `ONDEVICE_PROJECTS` config.
  Cross-ref 0006, which states failed turns "keep the server's spoken generic
  notice" - but in on-device mode the server produces no notice to keep.

Everything else in 0003 is CONFIRMED:
- pi failure persists a Failed turn with the real transcript:
  `talk.py:176-177` (`add_turn(..., failed=True)`).
- ASR failure persists a Failed turn with a placeholder transcript
  "(couldn't understand audio)": `talk.py:126`, persisted at `talk.py:150`.
- Generic spoken notice "Something went wrong, please try again":
  `talk.py:39`, synthesized at `talk.py:155-157` and `:182-184`.
- Notice runs through the same fallback chain as 0001 (via
  `_synthesize_audio` -> `tts_mod.synthesize`, `talk.py:246-255`).
- Technical detail kept in persisted text, not spoken: `reply = str(exc)` /
  `exc.detail` stored as the turn reply (`talk.py:128`, `:167-172`), while the
  spoken text is `GENERIC_FAILURE_NOTICE`.
- Failed turn never blocks the queue: the handler returns inside the `async with`,
  releasing the lock so the next turn proceeds (`talk.py:161`, `:188`).
- `failed` boolean in the API: `talk.py:291`; also on the turns list
  (`server/routes/chats.py:79`).
- ASR temp-file cleanup on failure: `talk.py:129-130` (`finally: tmp.unlink`).
  Note: the ADR's implementation note says the leak lives "in asr.py," but the fix
  moved temp-file ownership to `talk.py` (created `:118`, cleaned `:129-130`);
  `server/asr.py:31-37` stays bare and no longer owns the file. Leak is closed; the
  ADR note is stale only about location.

## 0006 on-device-speech - CONFIRMED

- Speak on-device when server sent no audio, or `audio_degraded`, or user picked
  on-device: `TalkViewModel+Audio.swift:13-18`; uses `AVSpeechSynthesizer` via
  `PlayerManager.speak` (`PlayerManager.swift:26-41`).
- On-device selectable, and when chosen the app sends `audio_response=false`:
  `TurnSettings.swift:20,31`, `ServerClient.swift:132-133`.
- Best system voice (premium -> enhanced -> en-US): `PlayerManager.swift:62-67`.
- Google-to-local fallback reports `audio_degraded: true`: `tts.py:65-66`
  returns `(path, True)`.
- Failed turns excluded from on-device speech: `TalkViewModel+Audio.swift:13`
  (`!response.failed`). CONFIRMED as written, but this exclusion is what produces
  the silent failed turn in on-device mode. See the 0003 DRIFTED entry.

## 0008 tools-read-and-note-not-edit - CONFIRMED

All concrete claims match:
- `--no-builtin-tools` (plus `--no-extensions`, `--no-skills`):
  `server/pi_runner.py:129-131`.
- Exactly 12 tools registered in `pi/tools.ts`: read_file, grep_search, glob_find,
  list_dir, tree (`:61,83,110,136,157`), git_log, git_show, git_blame, git_diff,
  git_branch, git_show_file (`:185,213,234,256,285,300`), write_file (`:324`).
- No shell tool; every tool execs via argv arrays (`pi.exec(cmd, args, ...)`,
  `tools.ts:58-59`), so metacharacters are inert.
- write_file restricted to `VOICE_SAVE_PATH` (default `docs/patchbay`) at the tool
  layer: `tools.ts:55`, boundary check `:341-349`. Server passes the same path via
  env: `pi_runner.py:111`.
- Git tools are inspection-only (log/show/blame/diff/branch/show_file); no
  stage/commit/push tool exists. System prompt reinforces it: `pi_runner.py:34`.

Documentation gap (not a boundary violation, not a drift): the server itself
auto-commits and auto-pushes saved notes when the client enables it
(`talk.py:151-154`, `:178-181`, `:194-197`; `_git_commit` `:305-355`, `_git_push`
`:374-390`). This does not contradict any 0008 claim: it is server-side, not an
agent tool; it stages only `save_path` (`talk.py:344`) onto a side `patchbay`
branch through an isolated `GIT_INDEX_FILE` without touching the working tree,
index, or current branch (`talk.py:305-350`), so no code is edited and the agent
still has no commit capability. But 0008 is silent that notes *do* get committed
and pushed when the feature is on, so a reader trusting 0008 alone would wrongly
conclude nothing is ever committed. Worth documenting.

---

## CONFIRMED (one line each)

- **0001 tts-fallback-chain** - one-way chain Google -> local -> static clip inside
  a single `synthesize()` call, per-chunk via `synthesize_chunked`
  (`tts.py:54-77`, `:80-105`); no fall-up from local to Google (`:74-77`); static
  clip is `assets/audio-unavailable.m4a` (`:26`, file present, 14.2K); `degraded`
  flag returned on the clip and surfaced as `audio_degraded` (`:68,77`,
  `talk.py:216-224`).
- **0004 single-chat-per-project** - `create_chat` returns the existing chat for a
  project dir (`server/chats.py:120-121`).
- **0005 audio-lifetime** - `Turn` has no audio field (`chats.py:15-23`); the turns
  API carries none (`routes/chats.py:79`); previous turn's audio evicted at the
  start of the next turn on that chat (`talk.py:83`, tracked in
  `_chat_audio_files`, set at `:158,185,205`); static clip never evicted
  (`:259,276`); `AUDIO_DIR` is a temp subdir (`config.py:108`). Caveat:
  `_chat_audio_files` is in-memory, so audio from before a server restart is left
  to OS temp eviction, not the deterministic policy.
- **0007 server-authoritative-turns** - successful fetch replaces the local cache
  rather than merging (`TalkViewModel.swift:47-53`, `turns = refreshed`); fetch
  failure keeps the cache (`:46` guard returns early); text turns append
  optimistically then reconcile (`:135,148-162`); server persists every turn before
  responding (`talk.py:192` etc.) and exposes `GET /api/chats/{id}/turns`
  (`routes/chats.py:75-79`). Method name `_mergeServerTurns` is stale (it
  replaces), but behavior matches the ADR.
