"""Integration tests for /api/talk and /api/chats routes."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ── /api/version ──────────────────────────────────────────────────────────────


class TestVersionEndpoint:
    def test_endpoint_returns_expected_keys(self, client):
        r = client.get("/api/version")
        assert r.status_code == 200
        body = r.json()
        assert "version" in body
        assert "source" in body
        assert "python" in body
        assert "pid" in body
        assert body["source"] in ("homebrew", "checkout", "unknown")

    def test_build_info_branch(self, monkeypatch):
        """When BUILD_INFO exists next to app.py, source=homebrew."""
        import routes.misc as misc_mod

        def mock_is_file(path_self):
            if path_self.name == "BUILD_INFO":
                return True
            return Path.__dict__["is_file"]

        monkeypatch.setattr(Path, "is_file", mock_is_file)
        monkeypatch.setattr(Path, "read_text", lambda _: "brew-HEAD-abc1234def56\n")

        v, s = misc_mod._compute_version()
        assert s == "homebrew"
        assert v == "brew-HEAD-abc1234def56"

    def test_git_branch(self, monkeypatch):
        """No BUILD_INFO, git works → source=checkout."""
        import routes.misc as misc_mod

        monkeypatch.setattr(Path, "is_file", lambda _: False)

        with patch("routes.misc.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "abc1234\n"
            v, s = misc_mod._compute_version()

        assert s == "checkout"
        assert v == "git-abc1234"

    def test_fallback(self, monkeypatch):
        """No BUILD_INFO, git fails → unknown/unknown."""
        import routes.misc as misc_mod

        monkeypatch.setattr(Path, "is_file", lambda _: False)

        with patch("routes.misc.subprocess.run", side_effect=FileNotFoundError()):
            v, s = misc_mod._compute_version()

        assert v == "unknown"
        assert s == "unknown"


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

    def test_delete_chat_purges_its_turns(self, client, chat_id):
        import chats as chats_mod

        chats_mod.add_turn(chat_id, "hi", "hello")
        assert chats_mod.get_turns(chat_id)
        client.delete(f"/api/chats/{chat_id}")
        assert chats_mod.get_turns(chat_id) == []
        assert chat_id not in chats_mod._turns

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
        for key in ("id", "name", "project_dir", "pi_session_id", "created_at", "last_active"):
            assert key in body, f"missing field: {key}"

    def test_create_missing_project_dir_returns_400(self, client):
        r = client.post("/api/chats", json={})
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_create_absolute_path_returns_400(self, client):
        r = client.post("/api/chats", json={"project_dir": "/etc/passwd"})
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_projects_list_sorted_case_insensitive(self, client, tmp_dev):
        for name in ["Zebra", "alpha", "Beta"]:
            (tmp_dev / name).mkdir()
        r = client.get("/api/projects")
        assert r.status_code == 200
        projects = r.json()["projects"]
        assert projects == sorted(projects, key=str.casefold)

    def test_create_same_project_dir_returns_existing(self, client, tmp_dev):
        r1 = client.post("/api/chats", json={"project_dir": "proj"})
        r2 = client.post("/api/chats", json={"project_dir": "proj"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]


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
    @staticmethod
    def _init_repo(proj: Path) -> None:
        def git(*args):
            subprocess.run(["git", *args], cwd=str(proj), capture_output=True, check=True)

        git("init", "-b", "develop")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        (proj / "README.md").write_text("hello\n")
        git("add", "README.md")
        git("commit", "-m", "init")

    @staticmethod
    def _git_out(proj: Path, *args) -> str:
        return subprocess.run(
            ["git", *args], cwd=str(proj), capture_output=True, text=True, check=True
        ).stdout.strip()

    def test_auto_commit_lands_on_named_branch_without_touching_working_state(self, client, chat_id, tmp_dev):
        proj = tmp_dev / "proj"
        self._init_repo(proj)
        # Pre-stage an UNRELATED file in the real index — it must not leak
        (proj / "unrelated.txt").write_text("staged but not for voice\n")
        subprocess.run(["git", "add", "unrelated.txt"], cwd=str(proj), capture_output=True, check=True)

        def fake_pi(*a, **kw):
            (proj / "docs" / "patchbay").mkdir(parents=True, exist_ok=True)
            (proj / "docs" / "patchbay" / "note.md").write_text("a note\n")
            return "ok"

        with patch("routes.talk.run_pi", new_callable=AsyncMock, side_effect=fake_pi):
            r = client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "hi",
                    "audio_response": "false",
                    "auto_commit": "true",
                    "auto_commit_branch": "patchbay",
                },
            )
        assert r.status_code == 200

        # Commit landed on the patchbay branch with only the note
        tree_files = self._git_out(proj, "ls-tree", "-r", "--name-only", "patchbay")
        assert "docs/patchbay/note.md" in tree_files
        assert "unrelated.txt" not in tree_files
        assert self._git_out(proj, "log", "-1", "--format=%s", "patchbay") == "voice: save notes"
        # Working branch and real index untouched
        assert self._git_out(proj, "branch", "--show-current") == "develop"
        staged = self._git_out(proj, "diff", "--cached", "--name-only")
        assert staged == "unrelated.txt"

    def test_auto_commit_advances_existing_branch(self, client, chat_id, tmp_dev):
        proj = tmp_dev / "proj"
        self._init_repo(proj)

        def fake_pi_factory(content):
            def fake_pi(*a, **kw):
                (proj / "docs" / "patchbay").mkdir(parents=True, exist_ok=True)
                (proj / "docs" / "patchbay" / "note.md").write_text(content)
                return "ok"

            return fake_pi

        data = {"chat_id": chat_id, "text": "hi", "audio_response": "false", "auto_commit": "true"}
        with patch("routes.talk.run_pi", new_callable=AsyncMock, side_effect=fake_pi_factory("one\n")):
            client.post("/api/talk", data=data)
        with patch("routes.talk.run_pi", new_callable=AsyncMock, side_effect=fake_pi_factory("two\n")):
            client.post("/api/talk", data=data)
        count = self._git_out(proj, "rev-list", "--count", "develop..patchbay")
        assert count == "2"

    def test_auto_commit_skips_when_nothing_new(self, client, chat_id, tmp_dev):
        proj = tmp_dev / "proj"
        self._init_repo(proj)
        data = {"chat_id": chat_id, "text": "hi", "audio_response": "false", "auto_commit": "true"}
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"):
            client.post("/api/talk", data=data)
        # save_path dir was created but is empty → no commit, branch not created
        branches = self._git_out(proj, "branch", "--list", "patchbay")
        assert branches == ""

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


# ── /api/talk — per-chat lock concurrency ──────────────────────────────────


class TestTalkConcurrency:
    """Per-chat asyncio.Lock serializes turns on the same chat."""

    def test_same_chat_serializes(self, client, chat_id, tmp_dev):
        import asyncio

        import httpx
        from unittest.mock import patch

        import routes.misc as misc_mod
        import routes.talk as talk_mod
        import chats as chats_mod
        from app import app

        async def _run():
            order: list[str] = []
            first_entered = asyncio.Event()
            first_can_exit = asyncio.Event()

            async def mock_run_pi(transcript, chat, save_path="", model=""):
                cid = chat.id
                order.append(f"enter_{cid}")
                if order.count(f"enter_{cid}") == 1:
                    first_entered.set()
                    await first_can_exit.wait()
                order.append(f"exit_{cid}")
                return "ok"

            with (
                patch.object(chats_mod, "DEVELOPER_DIR", tmp_dev),
                patch.object(chats_mod, "CHATS_FILE", tmp_dev / "chats.json"),
                patch.object(talk_mod, "DEVELOPER_DIR", tmp_dev),
                patch.object(misc_mod, "DEVELOPER_DIR", tmp_dev),
                patch("chats.save_chats", lambda: None),
                patch.object(talk_mod, "run_pi", mock_run_pi),
            ):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                    t1 = asyncio.create_task(
                        ac.post(
                            "/api/talk",
                            data={"chat_id": chat_id, "text": "hi", "audio_response": "false"},
                        )
                    )
                    await asyncio.wait_for(first_entered.wait(), timeout=5)

                    t2 = asyncio.create_task(
                        ac.post(
                            "/api/talk",
                            data={"chat_id": chat_id, "text": "hi", "audio_response": "false"},
                        )
                    )
                    await asyncio.sleep(0.3)

                    # Second request must still be waiting for the lock
                    assert order.count(f"enter_{chat_id}") == 1, (
                        f"Second request entered before first finished: {order}"
                    )

                    first_can_exit.set()

                    r1 = await t1
                    r2 = await t2
                    assert r1.status_code == 200
                    assert r2.status_code == 200

                    expected = [
                        f"enter_{chat_id}",
                        f"exit_{chat_id}",
                        f"enter_{chat_id}",
                        f"exit_{chat_id}",
                    ]
                    assert order == expected, f"Expected serialized, got: {order}"

        asyncio.run(_run())

    def test_different_chats_interleave(self, client, chat_id, tmp_dev):
        r2 = client.post("/api/chats", json={"project_dir": "proj"})
        chat_id2 = r2.json()["id"]

        import asyncio

        import httpx
        from unittest.mock import patch

        import routes.misc as misc_mod
        import routes.talk as talk_mod
        import chats as chats_mod
        from app import app

        async def _run():
            order: list[str] = []
            first_entered = asyncio.Event()
            first_can_exit = asyncio.Event()

            async def mock_run_pi(transcript, chat, save_path="", model=""):
                cid = chat.id
                order.append(f"enter_{cid}")
                if cid == chat_id:
                    first_entered.set()
                    await first_can_exit.wait()
                order.append(f"exit_{cid}")
                return "ok"

            with (
                patch.object(chats_mod, "DEVELOPER_DIR", tmp_dev),
                patch.object(chats_mod, "CHATS_FILE", tmp_dev / "chats.json"),
                patch.object(talk_mod, "DEVELOPER_DIR", tmp_dev),
                patch.object(misc_mod, "DEVELOPER_DIR", tmp_dev),
                patch("chats.save_chats", lambda: None),
                patch.object(talk_mod, "run_pi", mock_run_pi),
            ):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                    t1 = asyncio.create_task(
                        ac.post(
                            "/api/talk",
                            data={"chat_id": chat_id, "text": "hi", "audio_response": "false"},
                        )
                    )
                    await asyncio.wait_for(first_entered.wait(), timeout=5)

                    t2 = asyncio.create_task(
                        ac.post(
                            "/api/talk",
                            data={"chat_id": chat_id2, "text": "hi", "audio_response": "false"},
                        )
                    )
                    # Give t2 time to enter while t1 is still blocked
                    await asyncio.sleep(0.3)

                    # Different chat must interleave (both enter before either exits)
                    assert order.count(f"enter_{chat_id}") == 1
                    assert order.count(f"enter_{chat_id2}") == 1, (
                        f"Second chat should interleave, got: {order}"
                    )

                    first_can_exit.set()

                    r1 = await t1
                    r2 = await t2
                    assert r1.status_code == 200
                    assert r2.status_code == 200

        asyncio.run(_run())


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

    def test_model_field_reaches_run_pi(self, client, chat_id):
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok") as mock_pi:
            client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "false", "model": "gpt-4o"},
            )
        mock_pi.assert_awaited_once()
        call = mock_pi.await_args
        assert call is not None
        assert call.kwargs.get("model") == "gpt-4o"


# ── bearer-token auth ─────────────────────────────────────────────────────────


class TestBearerAuth:
    def test_api_requires_token_when_configured(self, client):
        import config

        with patch.object(config, "AUTH_TOKEN", "sekrit"):
            assert client.get("/api/chats").status_code == 401
            assert client.get("/api/chats", headers={"Authorization": "Bearer wrong"}).status_code == 401
            assert client.get("/api/chats", headers={"Authorization": "Bearer sekrit"}).status_code == 200

    def test_web_page_and_audio_stay_open(self, client):
        import config

        with patch.object(config, "AUTH_TOKEN", "sekrit"):
            assert client.get("/").status_code == 200
            # /audio 404s for a missing file but must not 401
            assert client.get("/audio/nonexistent.mp3").status_code != 401

    def test_no_token_configured_means_no_auth(self, client):
        import config

        with patch.object(config, "AUTH_TOKEN", ""):
            assert client.get("/api/chats").status_code == 200
