# Patchbay Voice product specification

Status: current-product specification with explicitly proposed future work. Reviewed against source on 2026-09-13. Existing ADRs remain the decision history; this document reconciles their promises with the implementation rather than assuming every promise is fully delivered.

## Product and audience

Patchbay Voice helps a developer understand a repository while away from an editor. A phone or browser sends a spoken or typed question to the developer's own server. A constrained pi agent reads the repository and returns a concise answer; on request, it saves a more detailed note for later.

The primary journey is learning about code with hands or eyes occupied. Open-app use is a valid experience today and an acceptable baseline for future continuous conversation. Locked-phone operation is desirable but not a verified product guarantee. Voice complements a coding agent that changes code; it does not replace that agent's editing and execution workflow.

The owner must be able to run a server, configure pi with a working model provider, and connect a client. This is currently a developer-operated tool, not a hosted consumer service.

## Core journeys

1. Connect: run the server beside the repositories, configure inference, and connect the iOS or web client. iOS accepts URL/token setup by QR or settings. Browser microphone input requires a secure context; plain HTTP on a remote address supports text but not browser microphone capture.
2. Select: choose a project directory under the configured project root. The app keeps one cumulative chat per project, including pi's separate session identifier.
3. Ask: hold and release the microphone button, or enter text. Audio is transcribed on the server; text bypasses transcription. The agent may read/search repository files and inspect git history through the bundled tool extension.
4. Hear or read: show the completed reply and, when audio is enabled, speak it using the configured server or device voice. Prefer a brief spoken answer. Technical error detail belongs in text; supported failure paths use a generic spoken notice.
5. Keep a note: explicitly request a note. The agent writes inside the configured notes directory. Optional deterministic server behavior commits that directory to a notes side branch and pushes the branch when enabled. Report the actual write/commit/push outcome; a spoken claim alone is not evidence of persistence.
6. Continue or reset: later turns reuse the project's conversation context. Reopening fetches server history; resetting drops the chat's turn history and pi session association. Audio is disposable, not a conversation archive.

## Capability boundary

a. The agent receives twelve parameterized read/search/history/note tools, with no built-in shell or arbitrary code-editing tools. The write tool is fenced to the configured notes directory. Treat these as implemented tool restrictions, not a claim that adversarial isolation has been formally proven.

b. Running tests, editing source, deploying, merging, and general workstation administration are outside Voice. The only intended repository mutation during a turn is a requested note and its optional fixed-shape persistence. See [scope and boundary](scope-and-boundary.md) and [ADR 0008](adr/0008-tools-read-and-note-not-edit.md).

c. The server and file access run on a machine the owner controls. This does not imply that all data stays on that machine: the selected inference provider receives prompts/tool content, and a cloud speech provider receives reply text. Local inference and speech are deployment options. Demos using LiteLLM small must not claim zero-cloud operation.

d. API authentication is optional and off by default. Audio URLs are not bearer-protected. The network/bind configuration matters; this is not an anonymously accessible multi-tenant service.

## Execution contract and current limits

A turn uses one held HTTP request. The server transcribes a completed clip, invokes one-shot pi with JSON events and a resumed session ID, stores the reply, and synthesizes requested audio. Observable pi tool events stream into server logs. Reply audio is returned as file URLs after synthesis; iOS fetches all chunks before playing the sequence. Neither token streaming to the client nor full-duplex conversational audio is implemented.

Same-chat requests wait on an in-memory asyncio lock. This serializes requests that reach the handler; it is not a durable submission inbox, an exactly-once delivery protocol, or crash recovery. The ordering point is lock acquisition, not when speech began on different clients. Process loss or a disconnected request may require recovery. Do not advertise that no input can ever be lost.

Transcript/reply history is stored atomically on the server and fetched by clients; iOS also keeps a local cache. Atomic file replacement protects a write from partial JSON, but is not a database transaction coordinating pi sessions, note writes and client delivery.

Known audio files for a chat are evicted at the next turn. The tracking map is in memory, so cleanup across server restarts is incomplete. Audio ephemerality is the intended lifecycle, not a verified secure-deletion guarantee. See [execution analysis](turn-execution-model.md) and [drift audit](adr-code-drift.md).

The eyes-free promise applies when audio responses are enabled and the client can play audio. Network loss, permissions, system interruptions and hardware routing need visible/audible recovery states. A disabled audio setting intentionally yields text only.

## Acceptance criteria and evidence

1. Repository grounding: a question about the selected repository produces an answer grounded in that repository, not an explanation of the assistant itself. Evidence: `evals/cases/001-repo-question-misread-as-agent-self-question` and the explicit-refusals case. The original failure and later correction remain preserved separately from replay inputs.
2. Concise answer, detailed note: requested detail goes into the note while the reply stays brief. Evidence: the short-speech/detailed-note golden case, captured write tool results and file contents. Existing single-turn evals do not establish multi-turn follow-up quality.
3. Correct details: answers preserve required status codes and redirect mechanisms even under imprecise wording. Evidence: the dangerous-commands golden case. The calibrated small-model baseline passes 3 of 4 development cases; the missing HTTP 400 detail remains a recorded failure. Do not present this as a solved or broadly benchmarked system.
4. Tool restrictions: available tools and API shape remain pinned; arguments do not invoke a shell. Evidence: `pi/tools.test.mts` and `pi/tools.ts`. Add targeted adversarial tests when changing path handling or tool capabilities.
5. Failure preservation and speech: supported ASR/pi failures preserve a failed turn and return generic notices; TTS failure does not discard a successful text reply. Evidence: `server/tests/test_routes.py`, `server/tests/test_logic.py`, and iOS playback decision tests. These tests do not prove device audio audibility.
6. Notes persistence: only the configured notes path is committed, the working branch/index remain intact, and push failure is reported independently. Evidence: `server/tests/test_git_ops.py` and a demo using an isolated repository plus local bare remote.
7. Conversation state: server reload/reset semantics, one chat per project, and same-chat serialization remain covered by server tests. Durable queues, abort/steer, and retry idempotency are not established features.
8. Demonstrability: both videos use actual app footage and captured production-path results, distinguish typed input from speech, label edited waits, and do not invent tool calls or imply that a local demo push reached GitHub. Source assets and captions must permit regeneration.

The evaluation suite uses Buddy-compatible capture/golden/corpus/experiment concepts, strict Pydantic grading output, and LiteLLM small for candidate and grader. Its scope is text behavior with historical README fixtures, not ASR, TTS, full-repository performance or physical-device operation. See [eval guide](../evals/README.md).

## Proposed continuous conversation

The desired future feature offers explicitly started continuous conversation, push-to-talk, and typed chat. Foreground operation is an acceptable first version; pocket operation is an extension. The current goal researches this feature without implementing it.

The initial candidate is native continuous capture with echo processing and local speech segmentation, retaining the existing server/pi path. Alternatives include streamed ASR and audio-aware endpoint detection. Research must compare interruption versus queued follow-up, distinguish stopping playback from cancelling server work, and preserve completed note effects honestly. See [continuous-voice research](continuous-voice-research.md) for source-backed options and device experiments.

Acceptance for any future release includes measured premature cutoffs, false submissions, response delay, interrupted playback, connectivity recovery and device resource use. Set numerical thresholds after collecting representative evidence; no fabricated performance target is implied here.
