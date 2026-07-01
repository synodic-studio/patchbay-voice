from __future__ import annotations

import asyncio
import base64
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import HTTPException

from config import AUDIO_DIR, GOOGLE_TTS_API_KEY, GOOGLE_TTS_VOICE, TTS_VOICE


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""
    for part in parts:
        if current and len(current) + 1 + len(part) < 120:
            current = current + " " + part
        else:
            if current:
                chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks or [text]


async def synthesize(text: str, provider: str = "say") -> Path:
    if provider == "google":
        return await _google_tts(text)
    return await _say_tts(text)


async def synthesize_chunked(text: str, provider: str = "say") -> list[Path]:
    sentences = _split_sentences(text)
    if len(sentences) == 1:
        return [await synthesize(text, provider)]
    results = await asyncio.gather(*[synthesize(s, provider) for s in sentences], return_exceptions=True)
    paths = []
    for r in results:
        if isinstance(r, Exception):
            raise r
        paths.append(r)
    return paths


async def _say_tts(text: str) -> Path:
    if not shutil.which("say"):
        raise HTTPException(500, "`say` not found — macOS only")

    uid = uuid.uuid4().hex
    aiff = AUDIO_DIR / f"{uid}.aiff"
    out = AUDIO_DIR / f"{uid}.m4a"

    def _run() -> None:
        subprocess.run(["say", "-v", TTS_VOICE, "-o", str(aiff), "--", text], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(out)], check=True)
        aiff.unlink(missing_ok=True)

    await asyncio.to_thread(_run)
    return out


async def _google_tts(text: str) -> Path:
    import httpx

    if not GOOGLE_TTS_API_KEY:
        raise HTTPException(500, "GOOGLE_TTS_API_KEY not configured — set env var or use provider=say")

    uid = uuid.uuid4().hex
    out = AUDIO_DIR / f"{uid}.mp3"

    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": GOOGLE_TTS_VOICE},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.0},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}",
            json=payload,
        )
        if resp.status_code != 200:
            raise HTTPException(502, f"Google TTS error {resp.status_code}: {resp.text[:200]}")

    out.write_bytes(base64.b64decode(resp.json()["audioContent"]))
    return out
