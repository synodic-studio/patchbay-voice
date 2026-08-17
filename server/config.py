from __future__ import annotations

import shutil
import subprocess
import tempfile
from os import environ
from pathlib import Path


def _pass_show(name: str) -> str:
    try:
        return subprocess.check_output(["pass", "show", name], text=True).strip()
    except Exception:
        return ""


HOST = environ.get("VOICE_HOST", "127.0.0.1")
PORT = int(environ.get("VOICE_PORT", "31552"))

# Optional shared secret. When set, all /api/* requests must carry
# "Authorization: Bearer <token>". Empty (the default) disables auth.
AUTH_TOKEN = environ.get("VOICE_AUTH_TOKEN", "").strip()

WHISPER_MODEL = environ.get("WHISPER_MODEL", "base.en")
WHISPER_DEVICE = environ.get("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE = environ.get("WHISPER_COMPUTE", "int8")
WHISPER_INITIAL_PROMPT = (
    "Technical discussion about software development, AI, and coding tools. "
    "Keywords: Python, TypeScript, SwiftUI, FastAPI, Pydantic, LangChain, LangSmith, "
    "LangGraph, LlamaIndex, litellm, OpenAI, Anthropic, Claude, pi coder, pi coding agent, "
    "faster-whisper, Whisper, RAG, evals, embeddings, RLHF, HuggingFace, Transformers, "
    "PyTorch, JAX, Tailscale, PocketBase, TypeBox, Tuist, SwiftLint, SwiftFormat, "
    "Patchbay, MCP, SDK, API, CLI, JSON, NDJSON, asyncio, FastAPI, uvicorn, GitHub, "
    "git, branch, commit, diff, refactor, endpoint, middleware, harness."
)

PI_BIN = shutil.which(environ.get("PI_BIN", "pi"))
PI_PROVIDER = environ.get("PI_PROVIDER", "litellm")
PI_MODEL = environ.get("PI_MODEL", "small")
# When set, forces every turn to this model regardless of what the client
# requests. Lets a locked-down or demo server pin one model even though the
# app always sends its own picker value (default "small").
FORCE_MODEL = environ.get("VOICE_FORCE_MODEL", "").strip()

DEVELOPER_DIR = Path(environ.get("DEVELOPER_DIR", "~/Developer")).expanduser()
CHATS_FILE = Path(environ.get("CHATS_FILE", "~/.voice-demo-chats.json").strip()).expanduser()
TURNS_FILE = Path(environ.get("TURNS_FILE", "~/.voice-demo-turns.json").strip()).expanduser()

TTS_VOICE = environ.get("TTS_VOICE", "Samantha")

# Local (no-credentials) TTS engine for the fallback chain's middle tier.
# Empty = auto-detect: macOS `say`, else piper (if PIPER_MODEL is set), else espeak.
LOCAL_TTS_ENGINE = environ.get("LOCAL_TTS_ENGINE", "").strip()
PIPER_BIN = environ.get("PIPER_BIN", "piper")
PIPER_MODEL = environ.get("PIPER_MODEL", "").strip()  # path to a piper .onnx voice
ESPEAK_BIN = environ.get("ESPEAK_BIN", "espeak-ng")
FFMPEG_BIN = environ.get("FFMPEG_BIN", "ffmpeg")

# Google TTS service account. Resolution order (all lazy — only read the first
# time Google TTS is actually used):
#   1. GOOGLE_TTS_SERVICE_ACCOUNT_JSON — the JSON inline (env)
#   2. GOOGLE_TTS_SERVICE_ACCOUNT_FILE — a path to the JSON file (best for
#      Linux/demo boxes with no `pass`; keep the file chmod 600)
#   3. pass show google-tts-service-account (the Mac default)
_google_tts_env_override = environ.get("GOOGLE_TTS_SERVICE_ACCOUNT_JSON")
_google_tts_file = environ.get("GOOGLE_TTS_SERVICE_ACCOUNT_FILE", "").strip()
_google_tts_creds: str | None = None


def get_google_tts_credentials() -> str:
    """Return the Google TTS service-account JSON, cached after first call."""
    global _google_tts_creds
    if _google_tts_creds is None:
        if _google_tts_env_override:
            _google_tts_creds = _google_tts_env_override
        elif _google_tts_file:
            try:
                _google_tts_creds = Path(_google_tts_file).read_text()
            except Exception:
                _google_tts_creds = ""
        else:
            _google_tts_creds = _pass_show("google-tts-service-account")
    return _google_tts_creds


# Force a TTS provider server-side regardless of what the client requests.
# The demo sets this to "google" so review always hears the good voice even
# though the app defaults to local `say`.
FORCE_TTS = environ.get("VOICE_FORCE_TTS", "").strip()

# Force the auto-commit branch server-side regardless of what the client sends.
# The branch is a free-text field in the app, so a demo or locked-down server
# can route notes to a known branch without anyone retyping it on a phone.
FORCE_COMMIT_BRANCH = environ.get("VOICE_FORCE_COMMIT_BRANCH", "").strip()

# Projects for which the server produces NO audio, so a client that supports it
# (the iOS app) speaks the reply with its own on-device voice. The demo uses one
# project on server-side Google TTS and another on the on-device voice so a
# reviewer can hear both.
ONDEVICE_PROJECTS = {
    p.strip() for p in environ.get("VOICE_ONDEVICE_PROJECTS", "").split(",") if p.strip()
}


GOOGLE_TTS_VOICE = environ.get("GOOGLE_TTS_VOICE", "en-US-Chirp3-HD-Schedar")
TTS_SPEAKING_RATE = float(environ.get("TTS_SPEAKING_RATE", "1.0"))

HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE.parent / "web"
ASSETS_DIR = HERE / "assets"  # server-internal assets (e.g. the TTS-unavailable clip)
EXTENSION_PATH = HERE.parent / "pi" / "tools.ts"

AUDIO_DIR = Path(tempfile.gettempdir()) / "voice-demo-audio"
AUDIO_DIR.mkdir(exist_ok=True)
