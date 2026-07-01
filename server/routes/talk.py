from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

import asr as asr_mod
import tts as tts_mod
from chats import _chats, save_chats
from config import AUDIO_DIR
from pi_runner import run_pi

router = APIRouter()


@router.post("/api/talk")
async def talk(
    chat_id: str = Form(...),
    audio: UploadFile = File(...),
):
    chat = _chats.get(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    suffix = ".webm" if audio.filename and audio.filename.endswith(".webm") else ".m4a"
    tmp = AUDIO_DIR / f"in-{uuid.uuid4().hex}{suffix}"
    tmp.write_bytes(await audio.read())

    t0 = time.time()
    transcript = await asr_mod.transcribe(tmp)
    tmp.unlink(missing_ok=True)
    t_asr = time.time() - t0

    if not transcript:
        return JSONResponse({"transcript": "", "reply": "No speech detected.", "audio_path": None})

    t1 = time.time()
    reply = await run_pi(transcript, chat)
    t_llm = time.time() - t1

    t2 = time.time()
    audio_path = await tts_mod.synthesize(reply)
    t_tts = time.time() - t2

    chat.last_active = time.time()
    save_chats()

    print(
        f"[turn] {transcript[:60]!r} asr={t_asr:.1f}s llm={t_llm:.1f}s tts={t_tts:.1f}s"
        f" | q={len(transcript)} a={len(reply)}"
    )

    return JSONResponse(
        {
            "transcript": transcript,
            "reply": reply,
            "audio_path": f"/audio/{audio_path.name}",
        }
    )
