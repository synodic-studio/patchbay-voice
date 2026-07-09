# CLAUDE.md

Guidance for AI agents (including `pi`) working in this repo. See README.md for architecture, setup, and API details.

## Web client: at parity with iOS

`web/index.html` was feature-frozen 2026-07-05 while the iOS app and server stabilized; the freeze was lifted 2026-07-08 and the web client brought up to parity. It now mirrors the iOS talk/settings surface: on-device (Web Speech) TTS alongside the server providers, the same failed-turn/`spoken_notice` and `audio_degraded` playback rules (a turn is never silent), auto-push + commit branch + AGENTS.md/CLAUDE.md fields, and localStorage-persisted conversation. Keep it in step with the iOS client and the `/api/talk` contract when either changes; it shares the same API.

## Spec-first workflow

This project is moving to a spec-first process using Matt Pocock's `/grill-with-docs` skill (installed at user scope) before building non-trivial features: interrogate the plan, capture vocabulary in `CONTEXT.md` and hard decisions in `docs/adr/` (created lazily as they come up), then write acceptance tests against that spec. Triggered by a bug (2026-07-04) where a Google TTS failure silently dropped an entire in-progress turn — a decision ("what happens when non-essential TTS fails") that was never written down and had no test covering it.
