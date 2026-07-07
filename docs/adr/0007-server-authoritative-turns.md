# The server is the source of truth for turn history

The app cached a chat's turns locally (in `UserDefaults`) and merged server turns into that cache by addition only — it never removed turns the server no longer had. So after a server-side reset, or any server-side deletion, stale turns lingered in the app until reinstall: a "refreshed" server did not refresh the app.

We decided the server is authoritative. On a successful fetch of a chat's turns, the server's list **replaces** the local cache rather than being merged into it. The local cache is kept only as an offline mirror: if the fetch fails because the server is unreachable, the app leaves what it already has.

This is safe because every turn is created through the server — `/api/talk` persists it before responding — so the server always holds everything the app has sent. There are no legitimate local-only turns to protect, so replace-on-fetch costs nothing real and makes a reset or deletion reflect immediately. Text turns still append optimistically for instant feedback (the app already knows the typed text), then reconcile against the server on the next load.

The alternative was a two-way sync with tombstones for deletions. We rejected it as overkill: the client never originates turns offline, so there is nothing to sync back, and a plain replace captures the whole requirement.
