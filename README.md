# Patchbay Voice

iOS voice interface to [pi](https://github.com/badlogicgames/pi-coding-agent), a multi-model AI coding agent. Speak into your phone, pi codes, it speaks back.

## What it is

A two-part system: an iOS app and a local server that runs on the same machine as pi.

You hold a button, say what you want built. The server transcribes it with faster-whisper, sends it to pi (via a custom extension bundled in the repo), and streams the response back as audio. The whole exchange is stored per-session so context accumulates across turns.

The design is headless-first: the iOS app is the only interface. There is no dashboard, no browser tab, no terminal you need to look at.

## Architecture

```
iOS app (Patchbay Voice)
  └── Hold to talk / type a message
      └── POST /api/talk → server
            ├── faster-whisper (local transcription)
            ├── pi --print --mode json --session <id> --extension server/static/pi-extension/tools.ts
            └── Google Cloud TTS or macOS say (audio response)
                └── Audio chunks streamed back to app
```

Sessions map one-to-one to directories under `~/Developer`. Each session carries a pi session ID so pi maintains context across turns.

## System Requirements

- **macOS** (server runs on your Mac)
- **[pi](https://github.com/badlogicgames/pi-coding-agent)** coding agent in `$PATH` (`pi` binary)
- **[uv](https://github.com/astral-sh/uv)** for Python dependency management
- **[Node.js](https://nodejs.org)** (required by pi to load the TypeScript extension)
- **faster-whisper** (bundled via uv — no manual install)
- **Google Cloud service account** with Text-to-Speech API enabled (optional — defaults to macOS `say`)

## Server

```bash
cd server
uv sync
uv run app.py
```

Runs on port 8800 by default. Configure with environment variables:

| Variable | Default | Description |
|---|---|---|
| `VOICE_HOST` | `127.0.0.1` | Bind address |
| `VOICE_PORT` | `8800` | Port |
| `PI_BIN` | `pi` | Path to pi binary |
| `PI_PROVIDER` | `litellm` | pi model provider |
| `PI_MODEL` | `small` | pi model alias |
| `DEVELOPER_DIR` | `~/Developer` | Root for project sessions |
| `WHISPER_MODEL` | `base.en` | faster-whisper model size |
| `TTS_VOICE` | `Samantha` | macOS say voice name |
| `TTS_SPEAKING_RATE` | `1.0` | Default speaking rate (0.5–2.0) |
| `GOOGLE_TTS_VOICE` | `en-US-Chirp3-HD-Schedar` | Google Cloud TTS voice |
| `GOOGLE_TTS_SERVICE_ACCOUNT_JSON` | *(from pass)* | Google service account JSON string |

To run as a persistent macOS service, copy and load the included plist:

```bash
cp com.synodic.patchbay-voice-server.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.synodic.patchbay-voice-server.plist
```

## The pi Extension

The file `server/static/pi-extension/tools.ts` is a pi extension that registers a single `write_file` tool. It constrains all file saves to a configured directory (`VOICE_SAVE_PATH` env var, defaulting to `docs/patchbay/` inside the session's project dir). This is the only tool pi has access to — no shell, no git, no arbitrary writes.

pi loads the extension automatically via `--extension` on every invocation.

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
- **Speaking rate** — adjustable 0.5×–2.0× slider in Settings, applied to both providers
- **Sessions** — one per repo, persisted across app launches; swipe to reset or delete
- **Turn history** — stored locally in UserDefaults until you reset the session
- **Write directory** — server constrains pi to a single save path per project
- **Dark graphite UI** — designed around the Patchbay Voice design system (1A Graphite)
- **Model switching** — any LiteLLM alias, switchable from Settings
