# CLAUDE.md

Guidance for AI agents (including `pi`) working in this repo. See README.md for architecture, setup, and API details.

## Web client: feature-frozen

`web/index.html` is feature-frozen as of 2026-07-05. Bug fixes only — no new features — until the iOS app and server are stable and specced out. Do not add web-client work to a task unless explicitly asked.

## Spec-first workflow

This project is moving to a spec-first process using Matt Pocock's `/grill-with-docs` skill (installed at user scope) before building non-trivial features: interrogate the plan, capture vocabulary in `CONTEXT.md` and hard decisions in `docs/adr/` (created lazily as they come up), then write acceptance tests against that spec. Triggered by a bug (2026-07-04) where a Google TTS failure silently dropped an entire in-progress turn — a decision ("what happens when non-essential TTS fails") that was never written down and had no test covering it.
