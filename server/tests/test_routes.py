"""Integration tests for /api/talk and /api/chats routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


class TestChatsRoutes:
    def test_list_empty(self, client):
        r = client.get("/api/chats")
        assert r.status_code == 200
        assert r.json()["chats"] == []

    def test_create_and_list(self, client, tmp_dev):
        r = client.post("/api/chats", json={"project_dir": "proj"})
        assert r.status_code == 200
        body = r.json()
        assert body["project_dir"] == "proj"

        listed = client.get("/api/chats").json()["chats"]
        assert len(listed) == 1
        assert listed[0]["id"] == body["id"]

    def test_create_bad_dir_returns_400(self, client):
        r = client.post("/api/chats", json={"project_dir": "../escape"})
        assert r.status_code == 400

    def test_delete_chat(self, client, chat_id):
        r = client.delete(f"/api/chats/{chat_id}")
        assert r.status_code == 200
        assert client.get("/api/chats").json()["chats"] == []

    def test_delete_unknown_returns_404(self, client):
        assert client.delete("/api/chats/nope").status_code == 404

    def test_reset_clears_session(self, client, chat_id):
        import chats as chats_mod

        chats_mod._chats[chat_id].pi_session_id = "old-session"
        r = client.post(f"/api/chats/{chat_id}/reset")
        assert r.status_code == 200
        assert chats_mod._chats[chat_id].pi_session_id is None


class TestTalkRoute:
    def test_no_input_returns_400(self, client, chat_id):
        r = client.post("/api/talk", data={"chat_id": chat_id})
        assert r.status_code == 400

    def test_unknown_chat_returns_404(self, client):
        r = client.post("/api/talk", data={"chat_id": "nope", "text": "hi"})
        assert r.status_code == 404

    def test_text_turn_no_tts(self, client, chat_id):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Got it."):
            r = client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "hello",
                    "audio_response": "false",
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert body["transcript"] == "hello"
        assert body["reply"] == "Got it."
        assert body["audio_urls"] == []
        assert body["audio_url"] is None

    def test_text_turn_with_tts(self, client, chat_id, tmp_path):
        fake_audio = tmp_path / "out.m4a"
        fake_audio.write_bytes(b"audio")
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Here you go."),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=fake_audio),
        ):
            r = client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "speak to me",
                    "audio_response": "true",
                    "tts_provider": "say",
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert body["reply"] == "Here you go."
        assert len(body["audio_urls"]) == 1
        assert body["audio_url"] == body["audio_urls"][0]

    def test_chunked_audio(self, client, chat_id, tmp_path):
        chunks = [tmp_path / f"c{i}.m4a" for i in range(2)]
        for c in chunks:
            c.write_bytes(b"chunk")
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="One. Two."),
            patch("routes.talk.tts_mod.synthesize_chunked", new_callable=AsyncMock, return_value=chunks),
        ):
            r = client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "chunk me",
                    "audio_response": "true",
                    "chunked_audio": "true",
                },
            )
        assert r.status_code == 200
        assert len(r.json()["audio_urls"]) == 2

    def test_save_path_traversal_rejected(self, client, chat_id):
        r = client.post(
            "/api/talk",
            data={
                "chat_id": chat_id,
                "text": "hi",
                "save_path": "../../etc",
            },
        )
        assert r.status_code == 400

    def test_save_path_leading_dash_rejected(self, client, chat_id):
        r = client.post(
            "/api/talk",
            data={
                "chat_id": chat_id,
                "text": "hi",
                "save_path": "-rf bad",
            },
        )
        assert r.status_code == 400

    def test_create_agents_md(self, client, chat_id, tmp_dev):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="done."):
            r = client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "save something",
                    "audio_response": "false",
                    "save_path": "docs/notes",
                    "create_agents_md": "true",
                },
            )
        assert r.status_code == 200
        assert (tmp_dev / "proj" / "docs" / "notes" / "AGENTS.md").exists()

    def test_create_agents_md_not_overwritten(self, client, chat_id, tmp_dev):
        md = tmp_dev / "proj" / "docs" / "notes" / "AGENTS.md"
        md.parent.mkdir(parents=True)
        md.write_text("existing content")
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok."):
            client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "hi",
                    "audio_response": "false",
                    "save_path": "docs/notes",
                    "create_agents_md": "true",
                },
            )
        assert md.read_text() == "existing content"
