from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

import asr
from chats import _chats
from config import ASSETS_DIR, AUDIO_DIR, DEVELOPER_DIR, PI_BIN, PI_MODEL, PI_PROVIDER, STATIC_DIR, TTS_VOICE, WHISPER_MODEL

router = APIRouter()


# ── Version (computed once at import time) ──────────────────────────────────────


def _compute_version() -> tuple[str, str]:
    """Return (version, source) resolved once at startup."""
    server_dir = Path(__file__).resolve().parent.parent
    build_info = server_dir / "BUILD_INFO"
    if build_info.is_file():
        return build_info.read_text().strip(), "homebrew"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(server_dir),
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"git-{result.stdout.strip()}", "checkout"
    except Exception:
        pass
    return "unknown", "unknown"


SERVER_VERSION, SERVER_SOURCE = _compute_version()


@router.get("/")
def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text())


@router.get("/api/version")
def get_version():
    return {
        "version": SERVER_VERSION,
        "source": SERVER_SOURCE,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "pid": os.getpid(),
    }


@router.get("/healthz")
def healthz():
    return {
        "whisper_model": WHISPER_MODEL,
        "whisper_loaded": asr.is_loaded(),
        "pi_bin": PI_BIN,
        "pi_provider": PI_PROVIDER,
        "pi_model": PI_MODEL,
        "tts_voice": TTS_VOICE,
        "chats": len(_chats),
        "developer_dir": str(DEVELOPER_DIR),
    }


@router.get("/api/projects")
def list_projects():
    try:
        dirs = sorted(
            (d.name for d in DEVELOPER_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")), key=str.casefold
        )
        return {"projects": dirs}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.get("/audio/{name}")
def get_audio(name: str):
    safe_name = Path(name).name
    path = AUDIO_DIR / safe_name
    if not path.exists():
        # Static fallback clips (e.g. the TTS-unavailable notice) live in
        # ASSETS_DIR, not AUDIO_DIR — check there before giving up.
        asset_path = ASSETS_DIR / safe_name
        if asset_path.is_file() and asset_path.parent == ASSETS_DIR:
            path = asset_path
        else:
            raise HTTPException(404, "audio expired")
    if path.suffix == ".m4a":
        media = "audio/mp4"
    elif path.suffix == ".mp3":
        media = "audio/mpeg"
    else:
        media = "application/octet-stream"
    return FileResponse(path, media_type=media)
