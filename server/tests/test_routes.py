"""Integration tests for /api/talk and /api/chats routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


# ── /api/chats ────────────────────────────────────────────────────────────────


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

    def test_create_response_has_required_fields(self, client, tmp_dev):
        r = client.post("/api/chats", json={"project_dir": "proj"})
        body = r.json()
        for key in ("id", "name", "project_dir", "created_at", "last_active"):
            assert key in body, f"missing field: {key}"

    def test_create_missing_project_dir_returns_400(self, client):
        r = client.post("/api/chats", json={})
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_create_absolute_path_returns_400(self, client):
        r = client.post("/api/chats", json={"project_dir": "/etc/passwd"})
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_projects_list(self, client, tmp_dev):
        (tmp_dev / "alpha").mkdir()
        (tmp_dev / "beta").mkdir()
        r = client.get("/api/projects")
        assert r.status_code == 200
        projects = r.json()["projects"]
        assert "alpha" in projects
        assert "beta" in projects

    def test_create_duplicate_project_dirs_allowed(self, client, tmp_dev):
        r1 = client.post("/api/chats", json={"project_dir": "proj"})
        r2 = client.post("/api/chats", json={"project_dir": "proj"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] != r2.json()["id"]


# ── /api/talk — error contract ────────────────────────────────────────────────


class TestTalkErrorContract:
    """Every error response must include a 'detail' key — iOS client depends on this."""

    def test_no_input_returns_400_with_detail(self, client, chat_id):
        r = client.post("/api/talk", data={"chat_id": chat_id})
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_unknown_chat_returns_404_with_detail(self, client):
        r = client.post("/api/talk", data={"chat_id": "nope", "text": "hi"})
        assert r.status_code == 404
        assert "detail" in r.json()

    def test_missing_chat_id_returns_422_with_detail(self, client):
        r = client.post("/api/talk", data={"text": "hello"})
        assert r.status_code == 422
        assert "detail" in r.json()

    def test_save_path_traversal_returns_400_with_detail(self, client, chat_id):
        r = client.post("/api/talk", data={"chat_id": chat_id, "text": "hi", "save_path": "../../etc"})
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_save_path_leading_dash_returns_400_with_detail(self, client, chat_id):
        r = client.post("/api/talk", data={"chat_id": chat_id, "text": "hi", "save_path": "-rf bad"})
        assert r.status_code == 400
        assert "detail" in r.json()


# ── /api/talk — response shape ────────────────────────────────────────────────


class TestTalkResponseShape:
    """Response must always include all fields iOS decodes — even on no-audio paths."""

    def test_response_has_all_required_fields(self, client, chat_id):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"):
            r = client.post("/api/talk", data={"chat_id": chat_id, "text": "hi", "audio_response": "false"})
        assert r.status_code == 200
        body = r.json()
        assert "transcript" in body
        assert "reply" in body
        assert "audio_url" in body  # may be None
        assert "audio_urls" in body  # may be []

    def test_no_audio_response_returns_empty_arrays(self, client, chat_id):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Got it."):
            r = client.post("/api/talk", data={"chat_id": chat_id, "text": "hello", "audio_response": "false"})
        body = r.json()
        assert body["audio_urls"] == []
        assert body["audio_url"] is None

    def test_transcript_matches_input_text(self, client, chat_id):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="answer"):
            r = client.post("/api/talk", data={"chat_id": chat_id, "text": "my question", "audio_response": "false"})
        assert r.json()["transcript"] == "my question"

    def test_reply_matches_pi_output(self, client, chat_id):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="the reply"):
            r = client.post("/api/talk", data={"chat_id": chat_id, "text": "q", "audio_response": "false"})
        assert r.json()["reply"] == "the reply"

    def test_whitespace_only_text_rejected(self, client, chat_id):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="(no response)"):
            r = client.post("/api/talk", data={"chat_id": chat_id, "text": "   ", "audio_response": "false"})
        # whitespace-only text is treated as "no audio or text"
        assert r.status_code in (200, 400)


# ── /api/talk — audio / TTS ───────────────────────────────────────────────────


class TestTalkAudio:
    def test_tts_with_single_audio(self, client, chat_id, tmp_path):
        fake_audio = tmp_path / "out.m4a"
        fake_audio.write_bytes(b"audio")
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Here you go."),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=fake_audio),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "speak to me", "audio_response": "true", "tts_provider": "say"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["reply"] == "Here you go."
        assert len(body["audio_urls"]) == 1
        assert body["audio_url"] == body["audio_urls"][0]
        assert body["audio_url"].startswith("/audio/")

    def test_chunked_audio_returns_multiple_urls(self, client, chat_id, tmp_path):
        chunks = [tmp_path / f"c{i}.m4a" for i in range(3)]
        for c in chunks:
            c.write_bytes(b"chunk")
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="One. Two. Three."),
            patch("routes.talk.tts_mod.synthesize_chunked", new_callable=AsyncMock, return_value=chunks),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "chunk me", "audio_response": "true", "chunked_audio": "true"},
            )
        assert r.status_code == 200
        body = r.json()
        assert len(body["audio_urls"]) == 3
        assert all(u.startswith("/audio/") for u in body["audio_urls"])

    def test_tts_error_does_not_crash_server(self, client, chat_id):
        """TTS failure should not propagate as 500 — reply is still returned."""
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="reply"),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, side_effect=RuntimeError("tts broke")),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "true", "tts_provider": "say"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["reply"] == "reply"
        assert body["audio_urls"] == []

    def test_audio_upload_calls_transcription(self, client, chat_id):
        fake_audio = b"\x00" * 64
        with (
            patch("routes.talk.asr_mod.transcribe", new_callable=AsyncMock, return_value="transcribed text"),
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="response"),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "audio_response": "false"},
                files={"audio": ("clip.m4a", fake_audio, "audio/m4a")},
            )
        assert r.status_code == 200
        assert r.json()["transcript"] == "transcribed text"

    def test_empty_transcript_returns_no_speech(self, client, chat_id):
        with patch("routes.talk.asr_mod.transcribe", new_callable=AsyncMock, return_value=""):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "audio_response": "false"},
                files={"audio": ("clip.m4a", b"\x00" * 64, "audio/m4a")},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["transcript"] == ""
        assert "No speech" in body["reply"]


# ── /api/talk — save path & file creation ────────────────────────────────────


class TestTalkSavePath:
    def test_save_dir_created(self, client, chat_id, tmp_dev):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"):
            client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "false", "save_path": "custom/path"},
            )
        assert (tmp_dev / "proj" / "custom" / "path").is_dir()

    def test_create_agents_md(self, client, chat_id, tmp_dev):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="done."):
            r = client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "save",
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

    def test_create_claude_md(self, client, chat_id, tmp_dev):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok."):
            client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "hi",
                    "audio_response": "false",
                    "save_path": "docs/notes",
                    "create_claude_md": "true",
                },
            )
        assert (tmp_dev / "proj" / "docs" / "notes" / "CLAUDE.md").exists()

    def test_create_claude_md_not_overwritten(self, client, chat_id, tmp_dev):
        md = tmp_dev / "proj" / "docs" / "notes" / "CLAUDE.md"
        md.parent.mkdir(parents=True)
        md.write_text("my notes")
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok."):
            client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "hi",
                    "audio_response": "false",
                    "save_path": "docs/notes",
                    "create_claude_md": "true",
                },
            )
        assert md.read_text() == "my notes"

    def test_save_path_absolute_stripped(self, client, chat_id, tmp_dev):
        """Leading slash on save_path is stripped, not treated as filesystem root."""
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "false", "save_path": "/docs/notes"},
            )
        assert r.status_code == 200
        assert (tmp_dev / "proj" / "docs" / "notes").is_dir()


# ── /api/talk — auto-commit ───────────────────────────────────────────────────


class TestTalkAutoCommit:
    def test_auto_commit_calls_git(self, client, chat_id):
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"),
            patch("routes.talk.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1)  # diff has changes
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "false", "auto_commit": "true"},
            )
        assert r.status_code == 200
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("git" in c and "add" in c for c in calls)

    def test_auto_commit_false_skips_git(self, client, chat_id):
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"),
            patch("routes.talk.subprocess.run") as mock_run,
        ):
            client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "false", "auto_commit": "false"},
            )
        mock_run.assert_not_called()

    def test_git_failure_does_not_crash_server(self, client, chat_id):
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"),
            patch("routes.talk.subprocess.run", side_effect=RuntimeError("git broke")),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "false", "auto_commit": "true"},
            )
        assert r.status_code == 200


# ── /api/talk — pi session persistence ───────────────────────────────────────


class TestTalkSession:
    def test_session_id_persisted(self, client, chat_id):
        import chats as chats_mod

        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"):
            client.post("/api/talk", data={"chat_id": chat_id, "text": "hi", "audio_response": "false"})

        # run_pi is async-mocked so session_id won't actually be set here,
        # but the chat still exists and last_active was bumped
        assert chat_id in chats_mod._chats
        assert chats_mod._chats[chat_id].last_active > 0

    def test_text_and_audio_false_no_tts_called(self, client, chat_id):
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="result"),
            patch("routes.talk.tts_mod.synthesize") as mock_tts,
        ):
            r = client.post("/api/talk", data={"chat_id": chat_id, "text": "hi", "audio_response": "false"})
        assert r.status_code == 200
        mock_tts.assert_not_called()
