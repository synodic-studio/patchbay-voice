# Submitting during an in-progress turn queues, never blocks or drops

The server never refuses a submission because a previous turn on the same chat is still running. Every submission is accepted immediately and processed as an independent turn — its own transcript, its own pi invocation, its own reply — in strict FIFO order. This replaces two things: the server's per-chat lock, which previously just made the caller wait, and iOS's client-side `pendingText`, which held only the single most recent pending message and silently dropped anything sent before it.

Queued turns are never merged into one combined pi invocation. Two things you said are two things — collapsing them risks pi answering only the last one and silently ignoring the first, and it would blur the existing definition of a `Turn` as one transcript paired with one reply.

## Considered Options

**Grouped queueing** — merging turns that queue up back-to-back into a single combined pi invocation. Rejected for now as the default, but noted as a plausible future mode or user-configurable setting once independent-turn queueing has been used in practice.

**Steer** — `pi`'s own RPC-mode primitive for injecting a message into an *already-running* turn once its current tool call finishes, without waiting for the turn to fully complete (see `CONTEXT.md`). This is closer to what a "smart" queue could feel like, but it requires replacing the server's one-shot-subprocess-per-turn integration with a long-lived `pi --mode rpc` process per chat — a materially larger architectural change than anything else in this document. Deferred as its own future initiative rather than folded into this fix.
