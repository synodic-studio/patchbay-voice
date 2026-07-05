# Turn audio is ephemeral — it lives until the chat's next turn, not forever

`AUDIO_DIR` (`server/config.py`) is the OS temp directory with no application-level cleanup, and `Turn` has no field referencing its audio at all — history loaded via `GET /api/chats/{chat_id}/turns` never carries audio, only the live response from the turn that just ran does. We decided this is correct by design, not an oversight to fix by building permanent audio history: the transcript and reply text are the permanent record of a turn; audio is a one-time rendering of it, not an archive.

The concrete lifetime rule: a turn's audio survives until that same chat's *next* turn is generated, then gets deleted. This matches what iOS already does client-side — `TalkViewModel` holds the last turn's decoded audio in memory for its replay button, naturally superseded when the next turn's audio arrives — and extends the same rule to the server's on-disk files, replacing reliance on the OS's temp-file eviction with a deterministic policy: at most one turn's worth of audio per active chat, ever.

## Considered Options

**Permanent, replayable audio history** — would require `Turn` to store an audio reference, history-loading to expose it, and a real retention/storage policy. Rejected: this is a live voice conversation, not a podcast archive, and nothing about the product needs old audio to survive.

Web's replay affordance is out of scope for now — it doesn't have one, and adding it would be new feature work under the current web feature freeze (see the repo's `CLAUDE.md`).
