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
PORT = int(environ.get("VOICE_PORT", "8800"))

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

DEVELOPER_DIR = Path(environ.get("DEVELOPER_DIR", "~/Developer")).expanduser()
CHATS_FILE = Path(environ.get("CHATS_FILE", "~/.voice-demo-chats.json").strip()).expanduser()

TTS_VOICE = environ.get("TTS_VOICE", "Samantha")

# Google TTS service account: env override works as before, but the pass lookup
# is lazy — only invoked the first time Google TTS actually needs it.
_google_tts_env_override = environ.get("GOOGLE_TTS_SERVICE_ACCOUNT_JSON")
_google_tts_creds: str | None = None


def get_google_tts_credentials() -> str:
    """Return the Google TTS service-account JSON, cached after first call."""
    global _google_tts_creds
    if _google_tts_creds is None:
        if _google_tts_env_override:
            _google_tts_creds = _google_tts_env_override
        else:
            _google_tts_creds = _pass_show("google-tts-service-account")
    return _google_tts_creds


GOOGLE_TTS_VOICE = environ.get("GOOGLE_TTS_VOICE", "en-US-Chirp3-HD-Schedar")
TTS_SPEAKING_RATE = float(environ.get("TTS_SPEAKING_RATE", "1.0"))

HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE.parent / "web"
EXTENSION_PATH = HERE.parent / "pi" / "tools.ts"

AUDIO_DIR = Path(tempfile.gettempdir()) / "voice-demo-audio"
AUDIO_DIR.mkdir(exist_ok=True)
