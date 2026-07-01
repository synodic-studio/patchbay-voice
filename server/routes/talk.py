from __future__ import annotations

import subprocess
import sys
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

import asr as asr_mod
import tts as tts_mod
from chats import _chats, save_chats
from config import AUDIO_DIR, DEVELOPER_DIR
from pi_runner import run_pi

router = APIRouter()


@router.post("/api/talk")
async def talk(
    chat_id: str = Form(...),
    audio: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    audio_response: str = Form(default="true"),
    tts_provider: str = Form(default="say"),
    chunked_audio: str = Form(default="false"),
    save_path: str = Form(default="docs/patchbay/"),
    auto_commit: str = Form(default="false"),
    create_agents_md: str = Form(default="false"),
    create_claude_md: str = Form(default="false"),
):
    chat = _chats.get(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    want_audio = _truthy(audio_response)
    want_chunked = _truthy(chunked_audio)
    want_commit = _truthy(auto_commit)

    # Validate and resolve save_path
    clean_save = save_path.strip().lstrip("/")
    if ".." in Path(clean_save).parts:
        raise HTTPException(400, "save_path must not contain ..")
    project_dir = DEVELOPER_DIR / chat.project_dir
    abs_save = (project_dir / clean_save).resolve()
    if not str(abs_save).startswith(str(project_dir.resolve())):
        raise HTTPException(400, "save_path must be inside the project directory")

    # Create save directory and optional init files
    abs_save.mkdir(parents=True, exist_ok=True)
    if _truthy(create_agents_md):
        _ensure_file(abs_save / "AGENTS.md", "# Agent Notes\n\nContext saved by Patchbay Voice.\n")
    if _truthy(create_claude_md):
        _ensure_file(abs_save / "CLAUDE.md", "# Claude Context\n\nContext created by Patchbay Voice.\n")

    # Transcribe or use provided text
    t_asr = 0.0
    if text and text.strip():
        transcript = text.strip()
    elif audio is not None:
        suffix = ".webm" if audio.filename and audio.filename.endswith(".webm") else ".m4a"
        tmp = AUDIO_DIR / f"in-{uuid.uuid4().hex}{suffix}"
        tmp.write_bytes(await audio.read())
        t0 = time.time()
        transcript = await asr_mod.transcribe(tmp)
        tmp.unlink(missing_ok=True)
        t_asr = time.time() - t0
    else:
        raise HTTPException(400, "Provide audio or text")

    if not transcript:
        return JSONResponse({"transcript": "", "reply": "No speech detected.", "audio_url": None, "audio_urls": []})

    # Run pi
    t1 = time.time()
    reply = await run_pi(transcript, chat, save_path=clean_save)
    t_llm = time.time() - t1

    if want_commit:
        _git_commit(project_dir, clean_save)

    # TTS
    audio_urls: list[str] = []
    t2 = time.time()
    if want_audio and reply:
        try:
            if want_chunked:
                paths = await tts_mod.synthesize_chunked(reply, provider=tts_provider)
            else:
                paths = [await tts_mod.synthesize(reply, provider=tts_provider)]
            audio_urls = [f"/audio/{p.name}" for p in paths]
        except HTTPException:
            raise
        except Exception as exc:
            print(f"[tts] error: {exc}", file=sys.stderr)
    t_tts = time.time() - t2

    chat.last_active = time.time()
    save_chats()

    print(
        f"[turn] {transcript[:60]!r} asr={t_asr:.1f}s llm={t_llm:.1f}s tts={t_tts:.1f}s"
        f" | q={len(transcript)} a={len(reply)} chunks={len(audio_urls)} provider={tts_provider}"
    )

    return JSONResponse(
        {
            "transcript": transcript,
            "reply": reply,
            "audio_url": audio_urls[0] if audio_urls else None,
            "audio_urls": audio_urls,
        }
    )


def _truthy(val: str) -> bool:
    return val.lower() not in ("false", "0", "no", "")


def _ensure_file(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content)


def _git_commit(project_dir: Path, save_path: str) -> None:
    try:
        subprocess.run(["git", "add", save_path], cwd=str(project_dir), capture_output=True, timeout=10)
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(project_dir),
            capture_output=True,
            timeout=5,
        )
        if diff.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m", "voice: save notes"],
                cwd=str(project_dir),
                capture_output=True,
                timeout=15,
            )
    except Exception as exc:
        print(f"[git] commit failed: {exc}", file=sys.stderr)
