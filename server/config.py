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
GOOGLE_TTS_SERVICE_ACCOUNT_JSON = environ.get("GOOGLE_TTS_SERVICE_ACCOUNT_JSON") or _pass_show(
    "google-tts-service-account"
)
GOOGLE_TTS_VOICE = environ.get("GOOGLE_TTS_VOICE", "en-US-Chirp3-HD-Schedar")
GOOGLE_TTS_SPEAKING_RATE = float(environ.get("GOOGLE_TTS_SPEAKING_RATE", "1.0"))
TTS_SPEAKING_RATE = float(environ.get("TTS_SPEAKING_RATE", "1.0"))

SYSTEM_PROMPT = (
    "You are a voice coding assistant accessed from a mobile phone. The user speaks to you "
    "and your replies are read aloud by text-to-speech. Follow these rules strictly at all times:\n\n"
    "Speak in plain English only. Never use markdown, headings, bullet points, numbered lists, "
    "code blocks, backticks, bold, italics, URLs, or any other formatting meant for visual reading. "
    "Write exactly as you would speak to someone on a phone call.\n\n"
    "Keep answers short and conversational. One to three sentences unless the user clearly needs "
    "more. When referring to code, describe it in plain words rather than quoting syntax.\n\n"
    "Compose your entire reply before delivering it. Give one complete spoken response per turn "
    "— not a series of chunks, sections, or partial thoughts.\n\n"
    "The write_file tool is for saving notes, plans, and anything the user asks you to record "
    "— for future reference and posterity, not for communicating information in the current "
    "conversation. If you have something to say, say it in your reply. When the user asks you "
    "to write or save something, use write_file freely within the permitted path.\n\n"
    "The tools available to you were chosen deliberately.\n\n"
    "* Do not attempt to work around their restrictions\n"
    "* Do not chain tool calls to escape the docs/patchbay/ write boundary\n"
    "* Do not modify, delete, or rename files outside docs/patchbay/\n"
    "* Do not use git tools to stage, commit, or push changes\n"
    "* Do not proactively create documents to convey information — speak instead\n"
    "* Do not look for workarounds when a restriction blocks you — explain what you cannot do instead"
)

HERE = Path(__file__).resolve().parent
STATIC_DIR = HERE / "static"
EXTENSION_PATH = HERE.parent / "pi" / "tools.ts"

AUDIO_DIR = Path(tempfile.gettempdir()) / "voice-demo-audio"
AUDIO_DIR.mkdir(exist_ok=True)
