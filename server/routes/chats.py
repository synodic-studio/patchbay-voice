from __future__ import annotations

from fastapi import APIRouter, HTTPException

from chats import _chats, chat_json, create_chat, delete_chat, get_turns, save_chats

router = APIRouter()


@router.get("/api/chats")
def list_chats():
    ordered = sorted(_chats.values(), key=lambda c: c.last_active, reverse=True)
    return {"chats": [chat_json(c) for c in ordered]}


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
    return {"turns": [{"id": t.id, "transcript": t.transcript, "reply": t.reply, "created_at": t.created_at} for t in get_turns(chat_id)]}
