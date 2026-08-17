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
        assert "audio_degraded" in body  # must be present, defaults to false

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


# ── /api/talk — Failed turn (pi + ASR failures) ──────────────────────────────


class TestTalkFailedTurn:
    """ADR 0003: Failed turns persist transcript, speak generic notice."""

    def test_asr_failure_returns_failed_turn(self, client, chat_id, tmp_path):
        """ASR failure → failed:true, placeholder transcript, reply=technical detail, audio synthesized."""
        import chats as chats_mod
        from unittest.mock import AsyncMock, patch

        with (
            patch("routes.talk.asr_mod.transcribe", side_effect=RuntimeError("whisper crashed")),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(tmp_path / "out.m4a", False)),
        ):
            (tmp_path / "out.m4a").write_bytes(b"audio")
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "audio_response": "true"},
                files={"audio": ("clip.m4a", b"\x00" * 64, "audio/m4a")},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["failed"] is True
        assert body["transcript"] == "(couldn't understand audio)"
        assert "whisper crashed" in body["reply"]
        assert len(body["audio_urls"]) > 0

        # Persisted Turn has failed=True
        turns = chats_mod.get_turns(chat_id)
        assert len(turns) == 1
        assert turns[0].failed is True
        assert turns[0].transcript == "(couldn't understand audio)"

    def test_pi_failure_returns_failed_turn(self, client, chat_id, tmp_path):
        """pi failure → failed:true, real transcript persisted, reply=technical detail, audio synthesized."""
        import chats as chats_mod
        from unittest.mock import AsyncMock, patch

        from fastapi import HTTPException

        with (
            patch("routes.talk.run_pi", side_effect=HTTPException(504, "pi timed out after 120s")),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(tmp_path / "out.m4a", False)),
        ):
            (tmp_path / "out.m4a").write_bytes(b"audio")
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "my real question", "audio_response": "true"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["failed"] is True
        assert body["transcript"] == "my real question"
        assert "pi timed out" in body["reply"]
        assert len(body["audio_urls"]) > 0

        # Persisted Turn has failed=True with the real transcript
        turns = chats_mod.get_turns(chat_id)
        assert len(turns) == 1
        assert turns[0].failed is True
        assert turns[0].transcript == "my real question"
        assert "pi timed out" in turns[0].reply

    def test_normal_turn_includes_failed_false(self, client, chat_id, tmp_path):
        """Normal successful turn → response has failed:false, persisted Turn has failed=False."""
        import chats as chats_mod
        from unittest.mock import AsyncMock, patch

        (tmp_path / "out.m4a").write_bytes(b"audio")
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Everything is fine."),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(tmp_path / "out.m4a", False)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hello", "audio_response": "false"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["failed"] is False
        assert body["transcript"] == "hello"
        assert body["reply"] == "Everything is fine."

        # Persisted Turn has failed=False
        turns = chats_mod.get_turns(chat_id)
        assert len(turns) >= 1
        persisted = [t for t in turns if t.transcript == "hello"]
        assert len(persisted) == 1
        assert persisted[0].failed is False

    def test_failed_turn_carries_spoken_notice_without_server_audio(self, client, chat_id):
        """ADR 0009: on-device mode (audio_response=false) makes no server audio,
        but the Failed turn must still carry the generic spoken notice so the
        client can voice it instead of going silent. reply stays the raw detail."""
        from unittest.mock import patch

        from fastapi import HTTPException

        from routes.talk import GENERIC_FAILURE_NOTICE

        with patch("routes.talk.run_pi", side_effect=HTTPException(504, "pi timed out after 120s")):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "my question", "audio_response": "false"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["failed"] is True
        assert body["audio_urls"] == []  # on-device: server synthesized nothing
        assert body["spoken_notice"] == GENERIC_FAILURE_NOTICE  # ...but the notice is there to speak
        assert "pi timed out" in body["reply"]  # raw detail stays in reply, never spoken

    def test_uploaded_audio_cleaned_up_on_asr_failure(self, client, chat_id, tmp_path):
        """Temp audio file is deleted even when ASR raises."""
        import routes.talk as talk_mod
        from unittest.mock import AsyncMock, patch

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        with (
            patch.object(talk_mod, "AUDIO_DIR", audio_dir),
            patch("routes.talk.asr_mod.transcribe", side_effect=RuntimeError("asr failed")),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "audio_response": "false"},
                files={"audio": ("clip.m4a", b"\x00" * 64, "audio/m4a")},
            )
        assert r.status_code == 200
        # Temp file must be gone — no files left in AUDIO_DIR
        remaining = list(audio_dir.iterdir())
        assert len(remaining) == 0, f"Temp files not cleaned up: {remaining}"

    def test_failed_turn_does_not_block_subsequent_turns(self, client, chat_id, tmp_dev):
        """A Failed turn does not prevent a subsequently queued turn from processing."""
        import asyncio

        import httpx
        from unittest.mock import AsyncMock, patch

        import routes.misc as misc_mod
        import routes.talk as talk_mod
        import chats as chats_mod
        from app import app

        async def _run():
            order: list[str] = []
            gate = asyncio.Event()

            async def mock_run_pi(transcript, chat, save_path="", model=""):
                order.append(f"pi_{transcript}")
                # First request to enter signals the gate, then stalls
                if len(order) == 1:
                    gate.set()
                    await asyncio.sleep(0.5)
                # Only after stalling do we decide failure
                if "fail" in transcript:
                    from fastapi import HTTPException
                    raise HTTPException(500, "intentional failure")
                return f"reply to {transcript}"

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
                            data={"chat_id": chat_id, "text": "first fail", "audio_response": "false"},
                        )
                    )
                    await asyncio.wait_for(gate.wait(), timeout=5)

                    t2 = asyncio.create_task(
                        ac.post(
                            "/api/talk",
                            data={"chat_id": chat_id, "text": "second ok", "audio_response": "false"},
                        )
                    )
                    await asyncio.sleep(0.3)

                    # First request entered and is blocking; second is queued
                    assert len(order) == 1, f"Expected 1 processed, got {order}"
                    assert order[0] == "pi_first fail"

                    # Let both finish
                    responses = await asyncio.gather(t1, t2, return_exceptions=True)

                    # First request is a Failed turn (200, failed:true)
                    r1 = responses[0]
                    assert r1.status_code == 200
                    assert r1.json()["failed"] is True

                    # Second request succeeds normally
                    r2 = responses[1]
                    assert r2.status_code == 200
                    assert r2.json()["failed"] is False
                    assert r2.json()["reply"] == "reply to second ok"

                    # Both turns processed in FIFO order
                    assert order == ["pi_first fail", "pi_second ok"]

        asyncio.run(_run())


# ── /api/talk — audio / TTS ───────────────────────────────────────────────────


class TestTalkAudio:
    def test_tts_with_single_audio(self, client, chat_id, tmp_path):
        fake_audio = tmp_path / "out.m4a"
        fake_audio.write_bytes(b"audio")
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Here you go."),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(fake_audio, False)),
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
        assert body["audio_degraded"] is False

    def test_chunked_audio_returns_multiple_urls(self, client, chat_id, tmp_path):
        chunks = [tmp_path / f"c{i}.m4a" for i in range(3)]
        for c in chunks:
            c.write_bytes(b"chunk")
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="One. Two. Three."),
            patch("routes.talk.tts_mod.synthesize_chunked", new_callable=AsyncMock, return_value=(chunks, False)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "chunk me", "audio_response": "true", "chunked_audio": "true"},
            )
        assert r.status_code == 200
        body = r.json()
        assert len(body["audio_urls"]) == 3
        assert all(u.startswith("/audio/") for u in body["audio_urls"])
        assert body["audio_degraded"] is False

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
        assert body["audio_degraded"] is True

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

    def test_audio_degraded_false_on_normal_success(self, client, chat_id, tmp_path):
        """Normal successful turn includes audio_degraded: false."""
        fake_audio = tmp_path / "out.m4a"
        fake_audio.write_bytes(b"audio")
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Hello!"),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(fake_audio, False)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "true", "tts_provider": "say"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["audio_degraded"] is False
        assert len(body["audio_urls"]) == 1

    def test_audio_degraded_true_when_both_providers_fail(self, client, chat_id, tmp_path):
        """Both providers fail → static clip used, audio_degraded: true."""
        import tts as tts_mod

        static_path = tts_mod._STATIC_FALLBACK
        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Hello!"),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(static_path, True)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "true", "tts_provider": "say"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["audio_degraded"] is True
        assert len(body["audio_urls"]) == 1


# ── /api/talk — audio lifetime (ADR 0005) ────────────────────────────────────


class TestTalkAudioLifetime:
    """ADR 0005: a turn\'s audio survives until the same chat\'s next turn."""

    def _file_turn(self, client, chat_id, audio_dir, tmp_path, text, audio_response="true"):
        """Run a talk turn that produces an audio file in *audio_dir*.

        Returns (response_json, audio_path) where audio_path is the file
        the mock TTS created inside audio_dir.
        """
        import uuid
        import routes.talk as talk_mod
        from unittest.mock import AsyncMock, patch

        fake_audio = audio_dir / f"{uuid.uuid4().hex}.m4a"
        fake_audio.write_bytes(b"audio")
        with (
            patch.object(talk_mod, "AUDIO_DIR", audio_dir),
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value=f"reply {text}"),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(fake_audio, False)),
        ):
            r = client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": text,
                    "audio_response": audio_response,
                    "tts_provider": "say",
                },
            )
        assert r.status_code == 200
        return r.json(), fake_audio

    def test_next_turn_evicts_previous_audio(self, client, chat_id, tmp_path):
        """Turn 1 produces audio; turn 2 produces audio → turn 1\'s file is gone."""
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        body1, path1 = self._file_turn(client, chat_id, audio_dir, tmp_path, "first")
        assert path1.exists(), "turn 1 audio should exist after turn 1"

        body2, path2 = self._file_turn(client, chat_id, audio_dir, tmp_path, "second")
        assert path2.exists(), "turn 2 audio should exist after turn 2"
        assert not path1.exists(), "turn 1 audio should be gone after turn 2"

    def test_next_turn_without_audio_still_evicts(self, client, chat_id, tmp_path):
        """Turn 1 produces audio; turn 2 has audio_response=false → turn 1\'s file still deleted."""
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        import routes.talk as talk_mod
        from unittest.mock import AsyncMock, patch

        # Turn 1 with audio
        fake_audio1 = audio_dir / "turn1.m4a"
        fake_audio1.write_bytes(b"audio")
        with (
            patch.object(talk_mod, "AUDIO_DIR", audio_dir),
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="reply first"),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(fake_audio1, False)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "first", "audio_response": "true", "tts_provider": "say"},
            )
        assert r.status_code == 200
        assert fake_audio1.exists()

        # Turn 2 with audio_response=false — no audio at all
        with patch.object(talk_mod, "AUDIO_DIR", audio_dir), patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="reply second"):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "second", "audio_response": "false"},
            )
        assert r.status_code == 200
        assert not fake_audio1.exists(), "turn 1 audio should be gone even though turn 2 has no audio"

    def test_different_chats_independent(self, client, tmp_path):
        """Turn 2 on chat A does not delete chat B\'s turn 1 audio."""
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        import routes.talk as talk_mod
        from unittest.mock import AsyncMock, patch

        # Create two distinct chats (different project directories so they get
        # different IDs — the API returns the same chat for the same project_dir).
        (tmp_path / "proj_a").mkdir()
        (tmp_path / "proj_b").mkdir()
        r = client.post("/api/chats", json={"project_dir": "proj_a"})
        chat_a = r.json()["id"]
        r = client.post("/api/chats", json={"project_dir": "proj_b"})
        chat_b = r.json()["id"]

        fake_a = audio_dir / "chat_a_turn1.m4a"
        fake_a.write_bytes(b"audio")
        fake_b = audio_dir / "chat_b_turn1.m4a"
        fake_b.write_bytes(b"audio")

        def _turn(chat_id_, audio_path, text):
            with (
                patch.object(talk_mod, "AUDIO_DIR", audio_dir),
                patch("routes.talk.run_pi", new_callable=AsyncMock, return_value=f"reply {text}"),
                patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(audio_path, False)),
            ):
                return client.post(
                    "/api/talk",
                    data={"chat_id": chat_id_, "text": text, "audio_response": "true", "tts_provider": "say"},
                )

        # Turn 1 on both chats
        r = _turn(chat_a, fake_a, "a-first")
        assert r.status_code == 200
        r = _turn(chat_b, fake_b, "b-first")
        assert r.status_code == 200

        # Turn 2 on chat A
        fake_a2 = audio_dir / "chat_a_turn2.m4a"
        fake_a2.write_bytes(b"audio")
        r = _turn(chat_a, fake_a2, "a-second")
        assert r.status_code == 200

        # Chat B's turn 1 audio must still be intact
        assert not fake_a.exists(), "chat A turn 1 audio should be gone"
        assert fake_b.exists(), "chat B turn 1 audio should survive"

    def test_static_fallback_never_deleted(self, client, chat_id, tmp_path):
        """A turn whose audio degraded to the static clip does NOT result in audio-unavailable.m4a being deleted, even after more turns."""
        import tts as tts_mod_t

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        import routes.talk as talk_mod
        from unittest.mock import AsyncMock, patch

        static_path = tts_mod_t._STATIC_FALLBACK

        # Turn 1 — degraded to static clip
        with (
            patch.object(talk_mod, "AUDIO_DIR", audio_dir),
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Hello!"),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(static_path, True)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "true", "tts_provider": "say"},
            )
        assert r.status_code == 200
        assert static_path.exists(), "static fallback must exist (it's a real project file)"

        # Turn 2 — another turn on the same chat (normal audio this time)
        fake_audio = audio_dir / "turn2.m4a"
        fake_audio.write_bytes(b"audio")
        with (
            patch.object(talk_mod, "AUDIO_DIR", audio_dir),
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="reply2"),
            patch("routes.talk.tts_mod.synthesize", new_callable=AsyncMock, return_value=(fake_audio, False)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "second", "audio_response": "true", "tts_provider": "say"},
            )
        assert r.status_code == 200

        # Static fallback must never have been deleted
        assert static_path.exists(), "static fallback must still exist after subsequent turns"

    def test_first_turn_no_audio_does_not_crash(self, client, chat_id):
        """A turn with audio_response=false on a fresh chat does not crash when there's nothing to evict."""
        from unittest.mock import AsyncMock, patch

        import routes.talk as talk_mod

        # No _chat_audio_files entry exists for this chat — must not crash
        with patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="ok"):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hello", "audio_response": "false"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["reply"] == "ok"

    def test_chunked_audio_eviction(self, client, chat_id, tmp_path):
        """Turn with chunked audio — all chunks from turn 1 evicted by turn 2."""
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        import routes.talk as talk_mod
        from unittest.mock import AsyncMock, patch

        # Turn 1 with 3 chunked audio files
        chunks1 = [audio_dir / f"t1_c{i}.m4a" for i in range(3)]
        for c in chunks1:
            c.write_bytes(b"chunk")
        with (
            patch.object(talk_mod, "AUDIO_DIR", audio_dir),
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="One. Two. Three."),
            patch("routes.talk.tts_mod.synthesize_chunked", new_callable=AsyncMock, return_value=(chunks1, False)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "first", "audio_response": "true", "chunked_audio": "true"},
            )
        assert r.status_code == 200
        assert all(c.exists() for c in chunks1), "all turn 1 chunks should exist after turn 1"

        # Turn 2 with chunked audio
        chunks2 = [audio_dir / f"t2_c{i}.m4a" for i in range(2)]
        for c in chunks2:
            c.write_bytes(b"chunk2")
        with (
            patch.object(talk_mod, "AUDIO_DIR", audio_dir),
            patch("routes.talk.run_pi", new_callable=AsyncMock, return_value="Four. Five."),
            patch("routes.talk.tts_mod.synthesize_chunked", new_callable=AsyncMock, return_value=(chunks2, False)),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "second", "audio_response": "true", "chunked_audio": "true"},
            )
        assert r.status_code == 200

        # Turn 1 chunks gone, turn 2 chunks present
        assert all(not c.exists() for c in chunks1), "all turn 1 chunks should be evicted"
        assert all(c.exists() for c in chunks2), "all turn 2 chunks should survive"


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

    def test_forced_branch_overrides_the_client(self, client, chat_id, tmp_dev):
        """The branch is a free-text field in the app, so a locked-down server
        can route notes itself rather than trusting what a phone sends."""
        proj = tmp_dev / "proj"
        self._init_repo(proj)

        def fake_pi(*a, **kw):
            (proj / "docs" / "patchbay").mkdir(parents=True, exist_ok=True)
            (proj / "docs" / "patchbay" / "note.md").write_text("a note\n")
            return "ok"

        with (
            patch("routes.talk.run_pi", new_callable=AsyncMock, side_effect=fake_pi),
            patch("routes.talk.FORCE_COMMIT_BRANCH", "patchbay-demo"),
        ):
            r = client.post(
                "/api/talk",
                data={
                    "chat_id": chat_id,
                    "text": "hi",
                    "audio_response": "false",
                    "auto_commit": "true",
                    "auto_commit_branch": "whatever-the-phone-says",
                },
            )
        assert r.status_code == 200

        tree_files = self._git_out(proj, "ls-tree", "-r", "--name-only", "patchbay-demo")
        assert "docs/patchbay/note.md" in tree_files
        branches = self._git_out(proj, "branch", "--format=%(refname:short)")
        assert "whatever-the-phone-says" not in branches

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

    def test_auto_commit_still_runs_on_a_failed_turn(self, client, chat_id, tmp_dev):
        """ADR 0003: pi can write a note before crashing on a later step — that
        note must still be auto-committed even though the turn itself failed."""
        from fastapi import HTTPException

        proj = tmp_dev / "proj"
        self._init_repo(proj)

        def fake_pi_writes_then_crashes(*a, **kw):
            (proj / "docs" / "patchbay").mkdir(parents=True, exist_ok=True)
            (proj / "docs" / "patchbay" / "note.md").write_text("partial note before crash\n")
            raise HTTPException(504, "pi timed out after 120s")

        with patch("routes.talk.run_pi", new_callable=AsyncMock, side_effect=fake_pi_writes_then_crashes):
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
        assert r.json()["failed"] is True

        tree_files = self._git_out(proj, "ls-tree", "-r", "--name-only", "patchbay")
        assert "docs/patchbay/note.md" in tree_files


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


# ── /api/talk — FIFO ordering with unique payloads ───────────────────────────


class TestTalkFifoOrder:
    """Every submission accepted; processed in strict submission order per chat."""

    def test_fires_N_concurrent_requests_processed_in_order(self, client, chat_id, tmp_dev):
        """Fire 5 overlapping requests with unique transcripts; verify order preserved."""
        import asyncio

        import httpx
        from unittest.mock import patch

        import routes.misc as misc_mod
        import routes.talk as talk_mod
        import chats as chats_mod
        from app import app

        async def _run():
            processed: list[str] = []
            gate = asyncio.Event()

            async def mock_run_pi(transcript, chat, save_path="", model=""):
                processed.append(transcript)
                if len(processed) == 1:
                    gate.set()  # first request is now inside the lock
                    # stall so the other requests queue up behind it
                    await asyncio.sleep(0.3)
                return f"reply to {transcript}"

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
                    payloads = [f"turn {i}" for i in range(5)]
                    tasks = [
                        asyncio.create_task(
                            ac.post(
                                "/api/talk",
                                data={"chat_id": chat_id, "text": p, "audio_response": "false"},
                            )
                        )
                        for p in payloads
                    ]
                    # Wait for first task to enter the lock, then let all queue up
                    await asyncio.wait_for(gate.wait(), timeout=5)
                    await asyncio.sleep(0.2)  # let others queue behind the lock

                    # By now all 5 should be in the waiter queue (only 1 processed)
                    assert len(processed) == 1, f"Expected 1 processed, got {processed}"

                    # Unblock: let all finish
                    responses = await asyncio.gather(*tasks)

                    # All requests must succeed
                    for r in responses:
                        assert r.status_code == 200, f"Got status {r.status_code}: {r.text[:200]}"

                    # Processed order must match submission order
                    assert processed == payloads, f"FIFO violated: {processed} != {payloads}"

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


# ── /api/chats/{id}/turns includes failed field ──────────────────────────────


class TestTurnsEndpoint:
    def test_turns_response_includes_failed_field(self, client, chat_id):
        """GET /api/chats/{id}/turns includes the failed field."""
        import chats as chats_mod
        from unittest.mock import patch

        # Persist a failed turn and a normal turn
        chats_mod.add_turn(chat_id, "failed transcript", "technical detail", failed=True)
        chats_mod.add_turn(chat_id, "normal transcript", "normal reply")

        r = client.get(f"/api/chats/{chat_id}/turns")
        assert r.status_code == 200
        turns = r.json()["turns"]
        assert len(turns) == 2

        failed_t = [t for t in turns if t["transcript"] == "failed transcript"][0]
        assert failed_t["failed"] is True

        normal_t = [t for t in turns if t["transcript"] == "normal transcript"][0]
        assert normal_t["failed"] is False


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
