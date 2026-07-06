from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

import asr as asr_mod
import tts as tts_mod
from chats import _chats, add_turn, save_chats
from config import AUDIO_DIR, DEVELOPER_DIR
from pi_runner import run_pi

router = APIRouter()

# Per-chat FIFO lock so overlapping turns on the same chat serialize in
# strict submission order.  Turns on different chats run fully concurrently.
#
# CPython's asyncio.Lock uses collections.deque internally: acquire() appends
# a waiter-future to the right and _wake_up_first() peeks the oldest waiter
# from the left.  This is documented as "fair scheduling" in the CPython source
# (Lib/asyncio/locks.py, comment: "calls will unblock tasks in FIFO order").
# No additional ordering mechanism is needed — see ADR 0002.
_talk_locks: dict[str, asyncio.Lock] = {}

# Per-chat audio file tracking: maps chat_id → list of Paths for the current/
# most-recent turn's audio files inside AUDIO_DIR.  The next turn on the same
# chat evicts these before generating its own audio — see ADR 0005.
_chat_audio_files: dict[str, list[Path]] = {}

# Generic spoken notice for Failed turns — never the raw technical detail.
GENERIC_FAILURE_NOTICE = "Something went wrong, please try again."


@router.post("/api/talk")
async def talk(
    chat_id: str = Form(...),
    audio: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    audio_response: str = Form(default="true"),
    tts_provider: str = Form(default="say"),
    speaking_rate: float = Form(default=1.0),
    chunked_audio: str = Form(default="false"),
    model: str = Form(default=""),
    save_path: str = Form(default="docs/patchbay/"),
    auto_commit: str = Form(default="false"),
    auto_commit_branch: str = Form(default="patchbay"),
    auto_push: str = Form(default="false"),
    create_agents_md: str = Form(default="false"),
    create_claude_md: str = Form(default="false"),
):
    chat = _chats.get(chat_id)
    if not chat:
        raise HTTPException(404, "Chat not found")

    # Serialize overlapping turns on the same chat
    if chat_id not in _talk_locks:
        _talk_locks[chat_id] = asyncio.Lock()
    async with _talk_locks[chat_id]:
        # ADR 0005: evict previous turn's audio before generating this one
        _evict_chat_audio(chat_id)
        want_audio = _truthy(audio_response)
        want_chunked = _truthy(chunked_audio)
        want_commit = _truthy(auto_commit)
        want_push = _truthy(auto_push)

        # Validate and resolve save_path; default when empty
        clean_save = save_path.strip().lstrip("/")
        if not clean_save:
            clean_save = "docs/patchbay"
        if clean_save.startswith("-") or ".." in Path(clean_save).parts:
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
            failed = False
            reply = None
        elif audio is not None:
            suffix = ".webm" if audio.filename and audio.filename.endswith(".webm") else ".m4a"
            tmp = AUDIO_DIR / f"in-{uuid.uuid4().hex}{suffix}"
            tmp.write_bytes(await audio.read())
            t0 = time.time()
            try:
                transcript = await asr_mod.transcribe(tmp)
                failed = False
                reply = None
            except Exception as exc:
                transcript = "(couldn't understand audio)"
                failed = True
                reply = str(exc)
            finally:
                tmp.unlink(missing_ok=True)
            t_asr = time.time() - t0
        else:
            raise HTTPException(400, "Provide audio or text")

        # No speech detected — not a failure, just empty input
        if not transcript and not failed:
            return JSONResponse(
                {
                    "transcript": "",
                    "reply": "No speech detected.",
                    "audio_url": None,
                    "audio_urls": [],
                    "audio_degraded": False,
                    "failed": False,
                }
            )

        # ASR failure — persist Failed turn with placeholder, speak generic notice
        if failed:
            add_turn(chat.id, transcript, reply, failed=True)
            if want_commit or want_push:
                _git_commit(project_dir, clean_save, branch=auto_commit_branch)
                if want_push:
                    _spawn_push(project_dir, auto_commit_branch)
            audio_urls, audio_degraded, audio_paths = await _synthesize_audio(
                GENERIC_FAILURE_NOTICE, want_audio, want_chunked, tts_provider, speaking_rate
            )
            _chat_audio_files[chat_id] = audio_paths
            chat.last_active = time.time()
            save_chats()
            return _failed_response(transcript, reply, audio_urls, audio_degraded)

        # Run pi
        t1 = time.time()
        try:
            reply = await run_pi(transcript, chat, save_path=clean_save, model=model)
        except HTTPException as exc:
            reply = exc.detail
            failed = True
        except Exception as exc:
            reply = str(exc)
            failed = True
        t_llm = time.time() - t1

        # pi failure — persist Failed turn with real transcript, speak generic notice
        if failed:
            add_turn(chat.id, transcript, reply, failed=True)
            if want_commit or want_push:
                _git_commit(project_dir, clean_save, branch=auto_commit_branch)
                if want_push:
                    _spawn_push(project_dir, auto_commit_branch)
            audio_urls, audio_degraded, audio_paths = await _synthesize_audio(
                GENERIC_FAILURE_NOTICE, want_audio, want_chunked, tts_provider, speaking_rate
            )
            _chat_audio_files[chat_id] = audio_paths
            chat.last_active = time.time()
            save_chats()
            return _failed_response(transcript, reply, audio_urls, audio_degraded)

        # Save turn immediately so it persists even if TTS fails
        if reply and reply != "(no response)":
            add_turn(chat.id, transcript, reply)

        if want_commit or want_push:
            _git_commit(project_dir, clean_save, branch=auto_commit_branch)
            if want_push:
                _spawn_push(project_dir, auto_commit_branch)

        # TTS — synthesize never raises for provider failures, so the
        # try/except here is only a safety net for truly unexpected bugs.
        t2 = time.time()
        audio_urls, audio_degraded, audio_paths = await _synthesize_audio(
            reply, want_audio, want_chunked, tts_provider, speaking_rate
        )
        _chat_audio_files[chat_id] = audio_paths
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
                "audio_degraded": audio_degraded,
                "failed": False,
            }
        )


async def _synthesize_audio(
    text: str,
    want_audio: bool,
    want_chunked: bool,
    tts_provider: str,
    speaking_rate: float,
) -> tuple[list[str], bool, list[Path]]:
    """Synthesize text to audio URLs.

    Returns (audio_urls, audio_degraded, audio_paths) where audio_paths
    contains the Paths inside AUDIO_DIR (never the static fallback clip).
    Never raises for provider failures — the caller always gets a valid
    (possibly empty) result.
    """
    audio_urls: list[str] = []
    audio_paths: list[Path] = []
    audio_degraded = False
    if want_audio and text:
        try:
            if want_chunked:
                paths, audio_degraded = await tts_mod.synthesize_chunked(
                    text, provider=tts_provider, speaking_rate=speaking_rate
                )
            else:
                path, audio_degraded = await tts_mod.synthesize(
                    text, provider=tts_provider, speaking_rate=speaking_rate
                )
                paths = [path]
            audio_urls = [f"/audio/{p.name}" for p in paths]
            # ADR 0005: only track files inside AUDIO_DIR — never the static
            # fallback clip (ASSETS_DIR / "audio-unavailable.m4a").
            audio_paths = [p for p in paths if p.parent == AUDIO_DIR]
        except Exception as exc:
            print(f"[tts] error: {exc}", file=sys.stderr)
            audio_degraded = True
    return audio_urls, audio_degraded, audio_paths


def _evict_chat_audio(chat_id: str) -> None:
    """Delete the previous turn's audio files for *chat_id*.

    Only files whose parent is AUDIO_DIR are ever removed — the static
    fallback clip (ASSETS_DIR / "audio-unavailable.m4a") is never touched.
    Called before generating a new turn's audio (see ADR 0005).
    """
    old = _chat_audio_files.pop(chat_id, None)
    if old:
        for p in old:
            if p.parent == AUDIO_DIR:
                p.unlink(missing_ok=True)


def _failed_response(
    transcript: str, reply: str, audio_urls: list[str], audio_degraded: bool
) -> JSONResponse:
    """Build the JSON response for a Failed turn."""
    return JSONResponse(
        {
            "transcript": transcript,
            "reply": reply,
            "audio_url": audio_urls[0] if audio_urls else None,
            "audio_urls": audio_urls,
            "audio_degraded": audio_degraded,
            "failed": True,
        }
    )


def _truthy(val: str) -> bool:
    return val.lower() not in ("false", "0", "no", "")


def _ensure_file(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content)


def _git_commit(project_dir: Path, save_path: str, branch: str = "patchbay") -> None:
    """Commit the save path to *branch* without switching to it.

    Builds the commit in a temporary index (GIT_INDEX_FILE) seeded from the
    branch tip, so the user's real index, working branch, and staged changes
    are never touched — and never leak into the auto-commit.
    """

    def _git(*args: str, env: dict | None = None) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, **(env or {})},
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {args[0]}: {result.stderr.strip() or result.returncode}")
        return result.stdout.strip()

    tmp_index = None
    try:
        # Parent: tip of target branch, or HEAD if the branch doesn't exist yet
        try:
            parent = _git("rev-parse", "--verify", f"refs/heads/{branch}")
            expected_old = parent  # guard against concurrent ref moves
        except RuntimeError:
            parent = _git("rev-parse", "HEAD")
            expected_old = ""  # ref must not exist yet

        fd, tmp_index = tempfile.mkstemp(prefix="voice-index-")
        os.close(fd)
        os.unlink(tmp_index)  # git wants to create the index file itself
        env = {"GIT_INDEX_FILE": tmp_index}

        # Seed the isolated index from the parent, stage only the save path
        _git("read-tree", parent, env=env)
        _git("add", "--", save_path, env=env)
        tree = _git("write-tree", env=env)

        if tree == _git("rev-parse", f"{parent}^{{tree}}"):
            return  # nothing new under save_path

        commit = _git("commit-tree", tree, "-p", parent, "-m", "voice: save notes", env=env)
        _git("update-ref", f"refs/heads/{branch}", commit, expected_old)
    except Exception as exc:
        print(f"[git] commit to {branch} failed: {exc}", file=sys.stderr)
    finally:
        if tmp_index:
            Path(tmp_index).unlink(missing_ok=True)


_push_tasks: set = set()


def _spawn_push(project_dir: Path, branch: str) -> None:
    """Fire-and-forget the push so it never delays the spoken reply. Safe to
    background because the app only offers auto-push when can_push is true
    (a git repo with a remote)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(asyncio.to_thread(_git_push, project_dir, branch))
    _push_tasks.add(task)
    task.add_done_callback(_push_tasks.discard)


def _git_push(project_dir: Path, branch: str = "patchbay") -> None:
    """Push *branch* to its remote (best-effort). No-op if there's no remote."""
    try:
        remotes = subprocess.run(
            ["git", "remote"], cwd=str(project_dir), capture_output=True, text=True, timeout=10,
        ).stdout.split()
        if not remotes:
            return
        target = "origin" if "origin" in remotes else remotes[0]
        result = subprocess.run(
            ["git", "push", target, f"refs/heads/{branch}:refs/heads/{branch}"],
            cwd=str(project_dir), capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"[git] push {branch} -> {target} failed: {result.stderr.strip()}", file=sys.stderr)
    except Exception as exc:
        print(f"[git] push {branch} failed: {exc}", file=sys.stderr)
