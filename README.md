# Patchbay Voice

iOS voice interface to Claude Code. Speak into your phone, Claude codes, it speaks back.

## What it is

A two-part system: an iOS app and a local server that runs on the same machine as Claude Code.

You hold a button, say what you want built. The server transcribes it with faster-whisper, sends it to Claude Code, and streams the response back as audio. The whole exchange is stored per-session so the context accumulates across turns. Clearing a session resets Claude's context.

The design is headless-first: the iOS app is the only interface. There is no dashboard, no browser tab, no terminal you need to look at.

## Architecture

```
iOS app (Patchbay Voice)
  └── Hold to talk / type a message
      └── POST /api/talk → server
            ├── faster-whisper (transcription)
            ├── Claude Code (claude --resume <session-id>)
            └── Google Cloud TTS or macOS say (audio response)
                └── Audio chunks streamed back to app
```

Sessions map one-to-one to directories under `~/Developer`. Each session carries a `--resume` ID so Claude maintains context across turns.

## Server

```bash
cd server
uv sync
uv run server.py
```

Runs on port 8000. Requires:
- `faster-whisper` (bundled via uv)
- `claude` CLI in PATH (Anthropic Claude Code)
- Google Cloud credentials if using Google TTS (otherwise defaults to macOS `say`)

Configure in Settings: server URL, model, TTS provider, save path.

## iOS App

Built with SwiftUI, targeting iOS 18+. Managed with [Tuist](https://tuist.io).

```bash
tuist generate --no-open
# then open PatchbayVoice.xcworkspace and run on device
```

Ships to TestFlight via Fastlane:

```bash
fastlane bump_build   # syncs with TestFlight, increments
fastlane beta         # build + upload + add to internal testers
```

## Features

- **Voice input** — hold the mic button, release to send; or switch to keyboard mode
- **TTS responses** — spoken replies via Google Cloud or macOS say, toggleable per-session
- **Sessions** — one per repo, persisted across app launches; swipe to reset or delete
- **Turn history** — stored locally in UserDefaults until you reset the session
- **Dark graphite UI** — designed around the Patchbay Voice design system (1A Graphite)
- **Model switching** — any LiteLLM alias, switchable from Settings
