from __future__ import annotations

import subprocess

from fastapi import APIRouter, HTTPException

from chats import _chats, chat_json, create_chat, delete_chat, get_turns, save_chats
from config import DEVELOPER_DIR

router = APIRouter()


def _git_capability(project_dir: str) -> dict:
    """Cheap, no-network check of what auto-commit/push can do for a project.

    can_commit → the project is a git repo (auto-commit works locally).
    can_push   → it's a git repo AND has a remote configured. The app uses
    these to enable/disable the toggles so neither is ever a silent no-op.
    """
    base = str((DEVELOPER_DIR / project_dir))
    try:
        is_repo = (
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=base, capture_output=True, text=True, timeout=5,
            ).returncode == 0
        )
    except Exception:
        is_repo = False
    has_remote = False
    if is_repo:
        try:
            has_remote = bool(
                subprocess.run(
                    ["git", "remote"], cwd=base, capture_output=True, text=True, timeout=5,
                ).stdout.strip()
            )
        except Exception:
            has_remote = False
    return {"can_commit": is_repo, "can_push": is_repo and has_remote}


@router.get("/api/chats")
def list_chats():
    ordered = sorted(_chats.values(), key=lambda c: c.last_active, reverse=True)
    return {"chats": [{**chat_json(c), **_git_capability(c.project_dir)} for c in ordered]}


@router.post("/api/chats")
def new_chat(body: dict):
    try:
        chat = create_chat(body.get("project_dir", "").strip())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return chat_json(chat)


@router.delete("/api/chats/{chat_id}")
def close_chat(chat_id: str):
    if chat_id not in _chats:
        raise HTTPException(404, "Chat not found")
    delete_chat(chat_id)
    return {"ok": True}


@router.post("/api/chats/{chat_id}/reset")
def reset_chat(chat_id: str):
    if chat_id not in _chats:
        raise HTTPException(404, "Chat not found")
    _chats[chat_id].pi_session_id = None
    save_chats()
    return chat_json(_chats[chat_id])


@router.get("/api/chats/{chat_id}/turns")
def list_turns(chat_id: str):
    if chat_id not in _chats:
        raise HTTPException(404, "Chat not found")
    return {"turns": [{"id": t.id, "transcript": t.transcript, "reply": t.reply, "created_at": t.created_at, "failed": t.failed} for t in get_turns(chat_id)]}
