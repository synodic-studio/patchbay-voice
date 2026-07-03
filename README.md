# Patchbay Voice

Voice interface to [pi](https://github.com/badlogic/pi-mono), a multi-model AI coding agent. Speak into your phone (or browser), pi codes, it speaks back.

## What it is

A two-part system: an iOS app and a local server that runs on the same machine as pi.

You hold a button, say what you want built. The server transcribes it with faster-whisper, sends it to pi (via a custom extension bundled in the repo), and streams the response back as audio. The whole exchange is stored per-session so context accumulates across turns.

Two clients ship with the repo: a native iOS app and a single-file web client served directly by the server at `GET /`. Both share the same API.

## Architecture

```
iOS app or web client (GET / → web/index.html)
  └── Hold to talk / type a message
      └── POST /api/talk → server
            ├── faster-whisper (local transcription)
            ├── pi --print --mode json --session <id> --extension pi/tools.ts
            └── Google Cloud TTS or macOS say (audio response)
                └── Audio chunks streamed back to client
```

Sessions map one-to-one to directories under `~/Developer`. Each session carries a pi session ID so pi maintains context across turns.

## System Requirements

- **macOS** (server runs on your Mac)
- **[pi](https://github.com/badlogic/pi-mono)** coding agent in `$PATH` (`pi` binary)
- **[uv](https://github.com/astral-sh/uv)** for Python dependency management
- **[Node.js](https://nodejs.org)** (required by pi to load the TypeScript extension)
- **faster-whisper** (bundled via uv — no manual install)
- **Google Cloud service account** with Text-to-Speech API enabled (optional — defaults to macOS `say`)

## Server

```bash
cd server
uv sync
uv run uvicorn app:app
```

Or use the convenience wrapper:

```bash
cd server
./run.sh
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

## Install via Homebrew

The server is also available via [synodic-studio/homebrew-synodic](https://github.com/synodic-studio/homebrew-synodic) (private repo, SSH):

```bash
brew tap synodic-studio/synodic git@github.com:synodic-studio/homebrew-synodic.git
brew install --HEAD synodic-studio/synodic/patchbay-voice-server
brew services start synodic-studio/synodic/patchbay-voice-server
```

The server binds `127.0.0.1` by default. To expose it on your LAN or Tailscale network, set `VOICE_HOST` (e.g. `0.0.0.0`, or a Tailscale `100.x.x.x` IP for device-specific access):

```bash
VOICE_HOST=0.0.0.0 patchbay-voice start          # foreground
launchctl setenv VOICE_HOST 0.0.0.0 && \
  brew services restart synodic-studio/synodic/patchbay-voice-server   # as a service
```

(Plain `VOICE_HOST=… brew services start` does not work — shell environment variables don't propagate into launchd-managed services.) Run `patchbay-voice urls` to print connection URLs.

> **Pick one approach.** The Homebrew formula and the repo-checkout LaunchAgent plist (above) manage the same service. Choose one — do not load both.

## The pi Extension

The file `pi/tools.ts` is a pi extension that registers a single `write_file` tool. It constrains all file saves to a configured directory (`VOICE_SAVE_PATH` env var, defaulting to `docs/patchbay/` inside the session's project dir). This is the only tool pi has access to — no shell, no git, no arbitrary writes.

pi loads the extension automatically via `--extension` on every invocation.

## Web Client

A single-file HTML/JS/CSS app at `web/index.html`, served by the server at `GET /`. No build step. Mirrors the iOS app: sessions list, talk screen with hold-to-talk mic, keyboard fallback, settings panel. Works in any modern browser.

> **Microphone requires a secure context.** The hold-to-talk feature uses `getUserMedia`, which browsers only allow on `https://` or `localhost`. The server serves plain `http://<lan-or-tailscale-ip>:8800`, so voice input will not work over LAN or Tailscale unless you front the server with HTTPS (e.g. `tailscale serve`). Text input always works.

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
