# One chat per project, deliberately — not an oversight

`create_chat` returns the existing chat for a project directory rather than creating a new one (`server/chats.py`). There is exactly one ongoing, cumulative conversation per project, for as long as that project exists in the app. This is a deliberate simplicity choice, not a limitation nobody's gotten around to fixing — though it may change later.

## Considered Options

**Multiple parallel chat threads per project** (e.g. a "refactor" thread and a separate "bug hunt" thread on the same repo) — considered and rejected for now in favor of simplicity. If the need for genuinely parallel, multi-threaded conversation about the same project shows up, the intended venue for that is Telegram group chats with topics, not an extension of patchbay-voice's own chat model.
