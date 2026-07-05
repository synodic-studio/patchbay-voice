# TTS failures degrade the turn; they never fail it

A Google TTS failure used to abort the entire `/api/talk` request via a re-raised `HTTPException`, after the reply had already been computed and persisted — so the client received an error and rendered nothing, even though the turn existed server-side. We decided audio is always best-effort: a synthesis failure must never prevent the transcript and reply from reaching the client.

To make that concrete, TTS synthesis follows a one-way fallback chain: **Google → `say` → a pre-recorded static "audio unavailable" clip.** It's one-way — if the user explicitly chose `say` and it fails, we do not fall *up* to Google, since that would silently start making a paid, credentialed API call the user didn't ask for. The clip is static rather than dynamically synthesized because by the time it's needed, every TTS engine on the box has already failed — there's nothing left to synthesize it with.

The chain lives inside a single synthesis call (not in the outer chunking/request-handling code), so multi-chunk replies get the same protection per-chunk automatically: one failed sentence chunk falls back independently, instead of discarding the whole reply's audio.

When the canned clip plays, the API response includes `audio_degraded: true` so the client can show an indicator — playing an unexplained, mismatched clip with no signal would be more confusing than the failure itself.
