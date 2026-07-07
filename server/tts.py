from __future__ import annotations

import asyncio
import base64
import re
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

from config import (
    ASSETS_DIR,
    AUDIO_DIR,
    ESPEAK_BIN,
    FFMPEG_BIN,
    GOOGLE_TTS_VOICE,
    LOCAL_TTS_ENGINE,
    PIPER_BIN,
    PIPER_MODEL,
    TTS_SPEAKING_RATE,
    TTS_VOICE,
)

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
        # Google failed — fall back to the local engine, but flag it degraded so
        # the client knows this chunk isn't the good voice. The iOS app then
        # speaks the whole reply on-device rather than playing a mix of Google
        # and the robotic local engine across a single response.
        try:
            path = await _local_tts(text, speaking_rate=speaking_rate)
            return (path, True)
        except Exception:
            return (_STATIC_FALLBACK, True)
    else:
        # local engine (the default), or any future provider
        try:
            path = await _local_tts(text, speaking_rate=speaking_rate)
            return (path, False)
        except Exception:
            # One-way rule: never fall *up* to Google if the user
            # explicitly chose the local engine and it failed.
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


def _pick_local_engine() -> str | None:
    """Choose the local (no-credentials) TTS engine.

    Honors LOCAL_TTS_ENGINE when set; otherwise auto-detects in preference
    order: macOS `say`, then piper (if a voice model is configured), then
    espeak. Returns None when nothing usable is installed (→ static clip).
    """
    if LOCAL_TTS_ENGINE:
        return LOCAL_TTS_ENGINE
    if shutil.which("say"):
        return "say"
    if PIPER_MODEL and shutil.which(PIPER_BIN):
        return "piper"
    if shutil.which(ESPEAK_BIN):
        return "espeak"
    return None


async def _local_tts(text: str, speaking_rate: float = 1.0) -> Path:
    engine = _pick_local_engine()
    if engine == "say":
        return await _say_tts(text, speaking_rate=speaking_rate)
    if engine == "piper":
        return await _piper_tts(text, speaking_rate=speaking_rate)
    if engine == "espeak":
        return await _espeak_tts(text, speaking_rate=speaking_rate)
    raise RuntimeError("no local TTS engine available")


def _encode_m4a(src: Path, dst: Path) -> None:
    """Encode any audio file to AAC/m4a with ffmpeg (cross-platform)."""
    subprocess.run(
        [FFMPEG_BIN, "-y", "-loglevel", "error", "-i", str(src), "-c:a", "aac", str(dst)],
        check=True,
    )


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


async def _piper_tts(text: str, speaking_rate: float = 1.0) -> Path:
    """Linux/local neural TTS via piper. Requires PIPER_MODEL (.onnx voice)."""
    if not PIPER_MODEL or not shutil.which(PIPER_BIN):
        raise RuntimeError("piper not configured (set PIPER_MODEL and install piper)")

    uid = uuid.uuid4().hex
    wav = AUDIO_DIR / f"{uid}.wav"
    out = AUDIO_DIR / f"{uid}.m4a"
    # piper's length_scale is inverse to speed: faster speech = shorter scale.
    length_scale = str(round(1.0 / max(0.25, min(4.0, speaking_rate)), 3))

    def _run() -> None:
        subprocess.run(
            [PIPER_BIN, "--model", PIPER_MODEL, "--length_scale", length_scale,
             "--output_file", str(wav)],
            input=text, text=True, check=True,
        )
        _encode_m4a(wav, out)
        wav.unlink(missing_ok=True)

    await asyncio.to_thread(_run)
    return out


async def _espeak_tts(text: str, speaking_rate: float = 1.0) -> Path:
    """Lightweight always-available local TTS via espeak-ng (robotic)."""
    if not shutil.which(ESPEAK_BIN):
        raise RuntimeError(f"`{ESPEAK_BIN}` not found")

    uid = uuid.uuid4().hex
    wav = AUDIO_DIR / f"{uid}.wav"
    out = AUDIO_DIR / f"{uid}.m4a"
    wpm = str(max(80, int(175 * speaking_rate)))  # espeak default is ~175 wpm

    def _run() -> None:
        # `--` stops option parsing so a reply starting with '-' can't be
        # smuggled in as an espeak flag (argv injection).
        subprocess.run([ESPEAK_BIN, "-s", wpm, "-w", str(wav), "--", text], check=True)
        _encode_m4a(wav, out)
        wav.unlink(missing_ok=True)

    await asyncio.to_thread(_run)
    return out


_google_creds = None
_google_creds_lock = threading.Lock()


def _get_google_token() -> str:
    global _google_creds
    import json

    import google.auth.transport.requests
    import google.oauth2.service_account

    from config import get_google_tts_credentials

    creds_json = get_google_tts_credentials()

    if not creds_json:
        raise RuntimeError("google-tts-service-account not found")

    # Serialize credential build + refresh. synthesize_chunked fires every
    # sentence at Google concurrently (each token fetch in its own thread); a
    # cold-cache race here had multiple threads building/refreshing the shared
    # credentials at once, and the losers failed Google and dropped to the
    # robotic local engine mid-reply. The lock makes the first thread build the
    # token and the rest reuse it.
    with _google_creds_lock:
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

    uid = uuid.uuid4().hex
    out = AUDIO_DIR / f"{uid}.mp3"
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": GOOGLE_TTS_VOICE},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": max(0.25, min(4.0, speaking_rate))},
    }

    # One retry: a transient blip on a single chunk shouldn't drop that chunk to
    # the local engine while its neighbors stay on Google (the "alternating voice").
    last_error: Exception = RuntimeError("Google TTS failed")
    for attempt in range(2):
        try:
            token = await asyncio.to_thread(_get_google_token)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://texttospeech.googleapis.com/v1/text:synthesize",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
            if resp.status_code == 200:
                out.write_bytes(base64.b64decode(resp.json()["audioContent"]))
                return out
            last_error = RuntimeError(f"Google TTS error {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            last_error = exc
        if attempt == 0:
            await asyncio.sleep(0.3)
    raise last_error
