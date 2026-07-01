from __future__ import annotations

import asyncio
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import HTTPException

from config import AUDIO_DIR, TTS_VOICE


async def synthesize(text: str) -> Path:
    if not shutil.which("say"):
        raise HTTPException(500, "`say` not found — macOS only")

    uid = uuid.uuid4().hex
    aiff = AUDIO_DIR / f"{uid}.aiff"
    out = AUDIO_DIR / f"{uid}.m4a"

    def _run():
        subprocess.run(["say", "-v", TTS_VOICE, "-o", str(aiff), "--", text], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(out)], check=True)
        aiff.unlink(missing_ok=True)

    await asyncio.to_thread(_run)
    return out
