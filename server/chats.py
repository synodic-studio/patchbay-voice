from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from config import CHATS_FILE, DEVELOPER_DIR, TURNS_FILE


@dataclass
class Turn:
    id: str
    chat_id: str
    transcript: str
    reply: str
    created_at: float = field(default_factory=time.time)
    failed: bool = False


@dataclass
class Chat:
    id: str
    name: str
    project_dir: str
    pi_session_id: str | None = field(default=None)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


_chats: dict[str, Chat] = {}
_turns: dict[str, list[Turn]] = {}  # chat_id -> [Turn]


def load_chats() -> None:
    # Update in-place — never rebind _chats. Route modules capture a reference
    # to this dict at import time; reassigning would leave them pointing at the
    # old empty dict while new chats are added to the new one.
    _chats.clear()
    _turns.clear()
    if not CHATS_FILE.exists():
        return
    try:
        raw = json.loads(CHATS_FILE.read_text())
        _chats.update(
            {k: Chat(**{f: c.get(f) for f in Chat.__dataclass_fields__}) for k, c in raw.get("chats", {}).items()}
        )
        # Load turns
        for t_raw in raw.get("turns", []):
            kwargs = {f: t_raw[f] for f in Turn.__dataclass_fields__ if f in t_raw}
            turn = Turn(**kwargs)
            _turns.setdefault(turn.chat_id, []).append(turn)
    except Exception as exc:
        print(
            f"[chats] *** WARNING *** load failed for {CHATS_FILE}: {exc} — "
            f"starting with empty chat list. The file may be corrupt.",
            file=sys.stderr,
        )


def save_chats() -> None:
    # Atomic write: write to a temp file in the same directory, then os.replace
    # so a crash mid-write doesn't corrupt the JSON file.
    all_turns = []
    for chat_turns in _turns.values():
        all_turns.extend(asdict(t) for t in chat_turns)
    data = json.dumps({"chats": {c.id: asdict(c) for c in _chats.values()}, "turns": all_turns})
    fd, tmp_path = tempfile.mkstemp(dir=str(CHATS_FILE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
        os.replace(tmp_path, str(CHATS_FILE))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def add_turn(chat_id: str, transcript: str, reply: str, failed: bool = False) -> Turn:
    turn = Turn(id=uuid.uuid4().hex, chat_id=chat_id, transcript=transcript, reply=reply, failed=failed)
    _turns.setdefault(chat_id, []).append(turn)
    save_chats()
    return turn


def get_turns(chat_id: str) -> list[Turn]:
    return _turns.get(chat_id, [])


def delete_chat(chat_id: str) -> None:
    del _chats[chat_id]
    _turns.pop(chat_id, None)
    save_chats()


def chat_json(c: Chat) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "project_dir": c.project_dir,
        "pi_session_id": c.pi_session_id,
        "created_at": c.created_at,
        "last_active": c.last_active,
    }


def create_chat(project_dir: str) -> Chat:
    rel = Path(project_dir)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("project_dir must be a relative name under DEVELOPER_DIR")
    base = (DEVELOPER_DIR / rel).resolve()
    if not base.is_dir() or DEVELOPER_DIR.resolve() not in base.parents:
        raise ValueError("project_dir must resolve to a directory under DEVELOPER_DIR")
    for existing in _chats.values():
        if existing.project_dir == str(rel):
            return existing
    chat = Chat(
        id=uuid.uuid4().hex,
        name=str(rel),
        project_dir=str(rel),
    )
    _chats[chat.id] = chat
    _turns[chat.id] = []
    save_chats()
    return chat
