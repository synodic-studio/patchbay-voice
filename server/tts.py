from __future__ import annotations

import asyncio
import base64
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from config import ASSETS_DIR, AUDIO_DIR, GOOGLE_TTS_VOICE, TTS_SPEAKING_RATE, TTS_VOICE

_SAY_BASE_WPM = 180  # approximate default WPM for macOS say voices
_STATIC_FALLBACK = ASSETS_DIR / "audio-unavailable.m4a"


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


async def synthesize(
    text: str, provider: str = "say", speaking_rate: float = TTS_SPEAKING_RATE
) -> tuple[Path, bool]:
    """Synthesize text to speech.

    Returns (audio_path, degraded) where degraded=True means the
    static fallback clip was used.  Never raises for provider-failure
    reasons.
    """
    if provider == "google":
        try:
            path = await _google_tts(text, speaking_rate=speaking_rate)
            return (path, False)
        except Exception:
            pass
        # Google failed — fall back to say
        try:
            path = await _say_tts(text, speaking_rate=speaking_rate)
            return (path, False)
        except Exception:
            return (_STATIC_FALLBACK, True)
    else:
        # say (the default), or any future provider
        try:
            path = await _say_tts(text, speaking_rate=speaking_rate)
            return (path, False)
        except Exception:
            # One-way rule: never fall *up* to Google if the user
            # explicitly chose say and it failed.
            return (_STATIC_FALLBACK, True)


async def synthesize_chunked(
    text: str, provider: str = "say", speaking_rate: float = TTS_SPEAKING_RATE
) -> tuple[list[Path], bool]:
    """Synthesize text in sentence chunks.

    Returns (paths, any_degraded).  Never raises for provider-failure
    reasons — per-chunk fallback is handled inside synthesize().
    """
    sentences = _split_sentences(text)
    if len(sentences) == 1:
        path, degraded = await synthesize(text, provider, speaking_rate=speaking_rate)
        return ([path], degraded)
    results = await asyncio.gather(
        *[synthesize(s, provider, speaking_rate=speaking_rate) for s in sentences],
        return_exceptions=True,
    )
    paths: list[Path] = []
    any_degraded = False
    for r in results:
        if isinstance(r, Exception):
            raise r
        path, degraded = r
        paths.append(path)
        if degraded:
            any_degraded = True
    return (paths, any_degraded)


async def _say_tts(text: str, speaking_rate: float = 1.0) -> Path:
    if not shutil.which("say"):
        raise RuntimeError("`say` not found — macOS only")

    uid = uuid.uuid4().hex
    aiff = AUDIO_DIR / f"{uid}.aiff"
    out = AUDIO_DIR / f"{uid}.m4a"
    wpm = str(max(80, int(_SAY_BASE_WPM * speaking_rate)))

    def _run() -> None:
        subprocess.run(["say", "-v", TTS_VOICE, "-r", wpm, "-o", str(aiff), "--", text], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(out)], check=True)
        aiff.unlink(missing_ok=True)

    await asyncio.to_thread(_run)
    return out


_google_creds = None


def _get_google_token() -> str:
    global _google_creds
    import json

    import google.auth.transport.requests
    import google.oauth2.service_account

    from config import get_google_tts_credentials

    creds_json = get_google_tts_credentials()

    if not creds_json:
        raise RuntimeError("google-tts-service-account not found in pass")

    if _google_creds is None:
        info = json.loads(creds_json)
        _google_creds = google.oauth2.service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

    if not _google_creds.valid:
        _google_creds.refresh(google.auth.transport.requests.Request())

    return _google_creds.token


async def _google_tts(text: str, speaking_rate: float = 1.0) -> Path:
    import httpx

    token = await asyncio.to_thread(_get_google_token)
    uid = uuid.uuid4().hex
    out = AUDIO_DIR / f"{uid}.mp3"

    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": GOOGLE_TTS_VOICE},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": max(0.25, min(4.0, speaking_rate))},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Google TTS error {resp.status_code}: {resp.text[:200]}")

    out.write_bytes(base64.b64decode(resp.json()["audioContent"]))
    return out
