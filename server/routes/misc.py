from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

import asr
from chats import _chats
from config import AUDIO_DIR, DEVELOPER_DIR, PI_BIN, PI_MODEL, PI_PROVIDER, STATIC_DIR, TTS_VOICE, WHISPER_MODEL

router = APIRouter()


@router.get("/")
def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text())


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
    path = AUDIO_DIR / Path(name).name
    if not path.exists():
        raise HTTPException(404, "audio expired")
    media = "audio/mp4" if path.suffix == ".m4a" else "audio/aiff"
    return FileResponse(path, media_type=media)
