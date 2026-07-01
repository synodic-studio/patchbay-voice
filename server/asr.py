from __future__ import annotations

import asyncio
import time
from pathlib import Path
from threading import Lock

from config import WHISPER_COMPUTE, WHISPER_DEVICE, WHISPER_INITIAL_PROMPT, WHISPER_MODEL

_model = None
_lock = Lock()


def is_loaded() -> bool:
    return _model is not None


def _get_model():
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel

            t0 = time.time()
            print(f"[whisper] loading {WHISPER_MODEL} ...")
            _model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
            print(f"[whisper] loaded in {time.time() - t0:.1f}s")
    return _model


async def transcribe(audio_path: Path) -> str:
    def _run():
        model = _get_model()
        segments, _ = model.transcribe(str(audio_path), initial_prompt=WHISPER_INITIAL_PROMPT)
        return " ".join(seg.text.strip() for seg in segments).strip()

    return await asyncio.to_thread(_run)
