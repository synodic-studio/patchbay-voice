# The server always ships the failure notice text, so a client that owns TTS can speak it

ADR 0003 says a Failed turn "speaks a generic notice," and ADR 0006 says the client speaks on-device when the server's audio is missing or degraded but deliberately excludes Failed turns from on-device speech, so it never reads a raw stack trace aloud. Each decision is correct alone. Together they left a hole: in on-device TTS mode the client sends `audio_response=false` (`ServerClient.swift`), so the server synthesizes nothing (`want_audio=false`, `routes/talk.py`), and the client, seeing a Failed turn, also refuses to speak. The result was total silence on a failure, in exactly the eyes-free situation ADR 0003 exists to prevent. It was reachable in the normal `ttsProvider == "ondevice"` setting, not just a demo config, and no test covered the seam.

The fix keeps both older decisions intact and closes the gap by giving the client the one thing it lacked: the notice text. The Failed-turn response now always carries a `spoken_notice` field holding the generic sentence (`GENERIC_FAILURE_NOTICE`), never the raw technical reply. When the server also produced notice audio (server-audio mode) the client plays that as before. When the server produced no audio (on-device mode, or a total TTS failure), the client speaks `spoken_notice` with `AVSpeechSynthesizer`. The raw failure detail stays in `reply` for on-screen debugging and is still never spoken. `spoken_notice` is a single source of truth: the same server constant that would have been synthesized, now also handed to the client so whichever side owns TTS can voice it.

The playback decision moved into a pure function, `TalkViewModel.playback(for:onDevice:)`, returning speak, play, or silent, so the failed-turn and on-device branches are unit-testable without audio hardware. That is where the regression lives now: a Failed turn with no server audio must return `.speak(notice)`, and must never return `.speak(rawReply)`.

## Considered Options

**Client hardcodes its own notice string.** Rejected: it duplicates the sentence across server and client, which can drift silently, and the client already receives a per-turn response from the server anyway, so there is no offline case that a hardcoded string would rescue.

**Have the server synthesize notice audio even in on-device mode.** Rejected: it defeats the point of on-device mode (no server round-trip for audio, a good local voice everywhere per ADR 0006) and would reintroduce the mixed-voice artifact that ADR 0006 removed.
