# The client speaks on-device when the server's audio isn't good enough

The TTS fallback chain (see docs/adr/0001) lives entirely server-side and ends at whatever local engine the server host happens to have. On macOS that is `say`; on Linux it is `espeak`, which sounds robotic. So a Google failure on a Linux server produced a jarring mix of a good Google voice and a bad espeak voice across a single chunked reply, and the app could do nothing about it because the server had already returned that (degraded) audio.

We decided to extend "audio is best-effort" to the client. When the server returns no audio, or flags `audio_degraded`, the app speaks the whole reply on-device with `AVSpeechSynthesizer` using the best system voice installed, instead of playing the server's rough audio. On-device is also a selectable TTS provider in Settings; when it is chosen the app tells the server to synthesize nothing (`audio_response=false`) and speaks locally.

The client always has a decent voice available (Apple's system voices), offline, with no round-trip and no server-side TTS setup. A supporting change makes a Google-to-local fallback report `audio_degraded: true` (it previously reported clean), which is what lets the client take over the whole reply uniformly and avoid the mixed-voice artifact. Failed turns are excluded: their reply text is the raw error, so they keep the server's spoken generic notice rather than reading a stack trace aloud.

The alternative was to fix the server's local engine (ship piper). We rejected it because it still depends on each server host having a good engine and does nothing for a plain remote or Linux server; the on-device voice is universal.
