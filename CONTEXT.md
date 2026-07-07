# Patchbay Voice

A voice interface to the `pi` coding agent: speak to it from a phone or browser, ask about a codebase, and it reads the code, inspects git history, saves Notes, and speaks the answer back. It does not edit your code (see docs/adr/0008).

## Language

**Chat**:
The single, ongoing, cumulative conversation for one project directory — at most one per project, for as long as that project exists in the app (a deliberate choice, see docs/adr/0004). Holds all of that project's turns and, separately, a `pi_session_id` — pi's own internal session, which can be reset independently without losing the chat's turn history.
_Avoid_: session (ambiguous with pi's own session — say "chat" for our object, "pi session" for pi's)

**Turn**:
One exchange in a chat: a user's transcript paired with the assistant's reply. Audio is a best-effort, ephemeral rendering of the reply — never a requirement for the turn to exist or be delivered, and never kept beyond the chat's next turn (see docs/adr/0005). The transcript and reply text are the permanent record; audio is not.
_Avoid_: message, exchange, request

**Degraded turn**:
A turn whose reply audio could not be synthesized by any provider, so a canned static clip plays in its place of the real reply audio. The transcript and text reply are always unaffected — only the audio quality degrades, never the turn's existence.
_Avoid_: failed turn, broken turn

**Failed turn**:
A turn where no reply was ever produced — pi timing out, crashing, or erroring, or transcription itself failing before pi is even reached. If a transcript exists, it's persisted (what the user said is never silently lost); if transcription itself failed, the transcript field holds a placeholder instead, since there are no real words to show. Either way, a short, fixed, generic notice is spoken through the same fallback chain as any other reply. Distinct from a `Degraded turn`, which has a complete, correct reply and only lost the ability to speak it — a Failed turn has no real reply to show, only the technical detail kept in its text for later debugging.
_Avoid_: error turn, degraded turn (these are not the same thing)

**Queued turn**:
A turn submitted while another turn on the same chat is still being processed. Held server-side in strict submission order and processed as its own independent turn once the chat is free — never dropped, never merged with another turn (grouping queued turns into one combined turn is a possible future mode, not the current behavior).
_Avoid_: pending message, backlog

**Steer** _(not yet implemented — considered and deferred, see docs/adr/0002)_:
Injecting a new message into a chat's in-progress turn so the agent picks it up as soon as its current tool call finishes and before its next LLM call — without aborting the turn in progress. Borrowed directly from `pi`'s own RPC-mode vocabulary (`streamingBehavior: "steer"`). Distinct from `abort` (forceful interrupt) and from queueing (waits for the turn to fully finish).
_Avoid_: interrupt, inject (use only when distinguishing from steer's non-interrupting semantics)

**Note**:
A file pi writes via the `write_file` tool to record something for later — notes, plans, anything the user asks it to save. Lives under a project's configured save path (`docs/patchbay/` by default), separate from the conversation itself: a Note is content pi produces as a side effect of a turn, not the turn's reply.
_Avoid_: memo, document, file (too generic — use Note for anything written via write_file specifically)

**On-device voice**:
A reply spoken by the app itself using the phone's built-in speech (`AVSpeechSynthesizer`), instead of audio synthesized by the server. Used automatically when the server sends no audio or a Degraded turn's audio, and also available as a selectable TTS provider (see docs/adr/0006). Independent of the server's own fallback chain.
_Avoid_: local TTS (ambiguous with the server's local engine — say "on-device" for the client, "local engine" for the server's say/espeak/piper)
