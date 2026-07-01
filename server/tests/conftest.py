from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add server/ to path so imports work from tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def tmp_dev(tmp_path):
    """Temp directory standing in for ~/Developer."""
    (tmp_path / "proj").mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_dev):
    """FastAPI TestClient with isolated state — no real disk I/O, no pass calls."""
    import chats as chats_mod
    import routes.misc as misc_mod
    import routes.talk as talk_mod

    chats_mod._chats.clear()

    with (
        patch.object(chats_mod, "DEVELOPER_DIR", tmp_dev),
        patch.object(chats_mod, "CHATS_FILE", tmp_dev / "chats.json"),
        patch.object(talk_mod, "DEVELOPER_DIR", tmp_dev),
        patch.object(misc_mod, "DEVELOPER_DIR", tmp_dev),
        patch("chats.save_chats", lambda: None),
    ):
        from app import app
        from fastapi.testclient import TestClient

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture
def chat_id(client, tmp_dev):
    r = client.post("/api/chats", json={"project_dir": "proj"})
    assert r.status_code == 200
    return r.json()["id"]
