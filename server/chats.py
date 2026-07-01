from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from config import CHATS_FILE, DEVELOPER_DIR


@dataclass
class Chat:
    id: str
    name: str
    project_dir: str
    pi_session_id: str | None = field(default=None)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


_chats: dict[str, Chat] = {}


def load_chats() -> None:
    # Update in-place — never rebind _chats. Route modules capture a reference
    # to this dict at import time; reassigning would leave them pointing at the
    # old empty dict while new chats are added to the new one.
    _chats.clear()
    if not CHATS_FILE.exists():
        return
    try:
        raw = json.loads(CHATS_FILE.read_text())
        _chats.update(
            {k: Chat(**{f: c.get(f) for f in Chat.__dataclass_fields__}) for k, c in raw.get("chats", {}).items()}
        )
    except Exception as exc:
        print(f"[chats] load failed: {exc}", file=sys.stderr)


def save_chats() -> None:
    CHATS_FILE.write_text(json.dumps({"chats": {c.id: asdict(c) for c in _chats.values()}}))


def chat_json(c: Chat) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "project_dir": c.project_dir,
        "created_at": c.created_at,
        "last_active": c.last_active,
    }


def create_chat(project_dir: str) -> Chat:
    rel = Path(project_dir)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("project_dir must be a relative name under DEVELOPER_DIR")
    base = (DEVELOPER_DIR / rel).resolve()
    if not base.is_dir() or DEVELOPER_DIR not in base.parents:
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
    save_chats()
    return chat
