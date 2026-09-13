# Continuous voice: research and decision brief

Research date: 2026-09-13. Status: proposal, no hot-mic behavior implemented or device validation performed. Scope: an explicitly started continuous conversation while the app is open is an acceptable baseline. Continuing with the iPhone locked or in a pocket is desirable, but is not a prerequisite for the first usable version. Push-to-talk and typed chat remain options. Interruption policy is deliberately open.

## Recommendation

Start with continuous native capture, Apple voice processing, local voice activity detection (VAD), and bounded utterance uploads to the existing server. Keep pi and LiteLLM `small`. Measure the resulting experience before adopting streaming ASR, a media server, or a different inference provider. Continuous listening and streaming inference are separate capabilities.

This is a proposed experiment, not an accepted architectural decision. Validate foreground behavior first during silence, response generation, audio playback, route changes, and network loss. Locked-screen behavior is a separate extension to investigate; failure there does not disqualify a useful foreground version.

## What exists

`ios/Project.swift` already declares the audio background mode and targets iOS 17. `AudioSessionManager.swift` uses playAndRecord with default mode, speaker output and Bluetooth HFP. `RecorderManager.swift` uses AVAudioRecorder to write a single AAC file at 16 kHz. It has no continuous frame pipeline or endpoint detector.

`server/asr.py` transcribes a completed file with faster-whisper. `/api/talk` serializes work with an in-memory per-chat lock, invokes one-shot pi, stores the answer, and produces audio before returning. The client fetches all response audio chunks before playback. The current pipeline is not full-duplex streaming. Its lock is not a durable queue. Stopping client playback does not establish cancellation of server work or reverse saved notes.

These observations come from the current source, not from a locked-device test. Source references: `ios/Sources/PatchbayVoice/Managers/`, `ios/Sources/PatchbayVoice/Views/TalkViewModel+Audio.swift`, `server/routes/talk.py`, `server/pi_runner.py`.

## Answers and alternatives

### Continuing in a pocket

Apple documents background recording/playback with the audio background mode and recommends voice-processing APIs for voice chat. The existing entitlement is a starting point, not proof of reliability. Use an explicitly initiated audio session and continuous capture while the conversation is active. Do not substitute silent playback, unrelated background modes, or periodic background jobs for a recording session. Interrupted audio needs explicit state and recovery behavior. See [Apple audio session guidance](https://developer.apple.com/library/archive/documentation/Audio/Conceptual/AudioSessionProgrammingGuide/AudioGuidelinesByAppType/AudioGuidelinesByAppType.html).

Recommendation: native iOS first. Treat browser foreground voice as a separate capability; do not promise browser pocket parity without independent validation. For a future pocket-capable mode, screen lock should not implicitly end the conversation. For a foreground-only version, explicitly communicate that limitation and pause or end listening predictably when backgrounded; do not leave the user believing the microphone is still listening. Force quitting the app is outside the continuous-session promise. On network loss, give an audible notice, bound temporary audio, and avoid silently replaying old requests on reconnect.

### Detecting the end of a turn

VAD detects speech, not whether a thought is complete. Start with a tunable silence window, speech-start hysteresis, a short pre-roll buffer to preserve initial consonants, and maximum utterance bounds. Compare settings on hesitant repository questions, code identifiers, background conversation, and pocket noise. Select thresholds from observed premature-cutoff and response-delay tradeoffs, not one universal magic constant.

[Silero VAD](https://github.com/snakers4/silero-vad) is an MIT-licensed candidate with 8/16 kHz support and ONNX deployment. Its published performance is not an iPhone battery benchmark; native packaging, resampling and frame handling still need validation. Apple’s muted-talker callbacks are documented for muted input, so they should not be assumed to provide a general active-input endpoint detector.

If silence-based detection cuts off too many thoughts, benchmark an audio-aware turn detector. [LiveKit’s current documentation](https://docs.livekit.io/agents/logic/turns/turn-detector/) describes an audio detector and a local CPU mini variant; its older text detector is deprecated. Check licensing, platform support and standalone integration before adopting it. Do not add the full LiveKit stack just to obtain a detector.

### Where audio goes

Recommended first experiment: retain a bounded rolling buffer locally, discard non-speech, send only completed utterances to the existing server, and remove transient clips after their defined lifecycle. This reduces continuous upload but still transmits detected speech; VAD cannot identify who is addressing the app.

Alternative: stream audio to the owned server for partial transcription and earlier endpoint decisions. This requires transport backpressure, sequence numbers, session identity, reconnect handling and partial/final transcript reconciliation. faster-whisper’s file VAD option alone does not supply that protocol. Its [upstream README](https://github.com/SYSTRAN/faster-whisper) points to separate streaming integrations.

A managed realtime speech service is another option, but changes audio routing, provider coupling and possibly the agent integration. It is not required merely to remove the talk button. No provider replacement is recommended yet.

### Speaking over the answer

Evaluate two modes with the same recordings:

a. Interrupt: confirmed user speech stops or ducks playback immediately, captures the new utterance, and marks the earlier answer as interrupted. A cough or false detection should be recoverable. Capture must continue while answering.

b. Follow-up: capture the new utterance while allowing playback to finish, then submit in order. This preserves completion but risks the user missing the answer while speaking. Bound pending turns and provide an audible acknowledgement.

Both need echo cancellation and a record of what was actually played. A generated answer is not necessarily a heard answer. Stopping playback, cancelling queued work, aborting active inference, and steering an agent are distinct operations. Any future abort protocol needs server acknowledgement and a clear outcome for completed tool effects. An already-written or pushed note cannot be described as undone merely because the user interrupted. The installed pi 0.80.3 RPC documentation defines `steer` after current tool calls and before the next model call, `follow_up` after the agent finishes, and `abort` for the current operation. These are capabilities of pi, not exposed Voice endpoints. A persistent RPC adapter still needs lifecycle, acknowledgements and persistence tests before adoption. Local source: `/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent/docs/rpc.md`, inspected 2026-09-13.

### Echo, headphones and playback

[Apple voice processing](https://developer.apple.com/videos/play/wwdc2023/10235/) provides echo cancellation, noise suppression and gain control through AVAudioEngine or Voice Processing I/O. Recommendation: use a common voice-processing audio graph for input and reply playback. Verify how existing AVAudioPlayer and AVSpeechSynthesizer paths interact with that graph; do not assume enabling processing on input alone solves every playback path.

Test speaker, wired/headset routes where available, Bluetooth HFP, headphone removal, route sample-rate changes, and system interruptions. Headphones reduce acoustic feedback but do not eliminate route or microphone problems. Pocket speaker use is a separate acoustic test from pocket use with a headset.

### Starting, pausing and ending

Recommend explicit start with an audible cue; a distinct paused state; explicit end that releases capture; and a visible listening indicator when foregrounded. Research a spoken end command and supported headset/lock-screen controls as redundant exits. A phrase quoted during a repository discussion must not accidentally end the session. Muting must clearly distinguish microphone capture from uploading. Automatic resumption after a system interruption should not surprise the user.

Apple requires recording consent and a clear visual or audible indication, and limits background services to their intended purpose. This informs the interaction design, not a guarantee of App Review approval. See [App Review Guidelines 2.5.4 and 2.5.14](https://developer.apple.com/app-store/review/guidelines/).

## Evidence needed before choosing implementation

1. Build an isolated native audio spike with timestamped capture, route, lifecycle, interruption and playback events. Establish open-app operation first on a physical iPhone, including quiet waiting and server response delays. Then repeat while locked to assess pocket support separately. Simulator results cannot establish pocket reliability.
2. Replay consented audio fixtures through candidate endpoint settings. Include long thinking pauses, self-correction, code names, silence, background speech, coughs, and playback leakage. Report false submissions, premature cutoffs, clipped starts and endpoint delay distributions.
3. Compare interrupt and follow-up policies on identical scenarios. Verify no duplicate turn or note on retry, no stale answer playback after interruption, and honest handling of completed side effects.
4. Measure speech-end to first audible answer, stage timings, bytes uploaded, memory growth, device thermal behavior and battery impact. Separate cold ASR/model startup from warm operation. No latency or battery claim is established by this research.
5. Exercise connectivity loss and reconnect, microphone permission changes, incoming calls, headphone removal and app termination. Record which failures recover automatically and which require a fresh user start.
6. Use outcomes to choose local segmentation versus streamed audio, endpoint detector, interruption default, and the scope of lock-screen controls. Keep text-only evals distinct from these audio/session tests.

## Relationship to the larger goal

The product spec and both subtitled demo videos should describe current behavior accurately. Continuous voice belongs in a proposed-future section until implemented and physically tested. The product video demonstrates repository understanding and useful notes; the engineering video shows actual pipeline events and behavioral evaluation. Neither should simulate hot mic as an existing feature.
