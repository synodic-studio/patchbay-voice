"""Unit tests for pure logic functions — no I/O, no mocking."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest


# ── tts._split_sentences ──────────────────────────────────────────────────


class TestSplitSentences:
    def test_single_sentence(self):
        from tts import _split_sentences

        assert _split_sentences("Hello world.") == ["Hello world."]

    def test_splits_long_text(self):
        from tts import _split_sentences

        # Each sentence is long enough that merging would exceed the 120-char threshold
        s1 = "The system has finished processing your request and the results are now available."
        s2 = "You can review the full output by navigating to the reports section of the dashboard."
        result = _split_sentences(f"{s1} {s2}")
        assert len(result) == 2
        assert all(s.strip() for s in result)

    def test_merges_short_fragments(self):
        from tts import _split_sentences

        # Short sentences stay merged — avoids tiny audio chunks with bad prosody
        result = _split_sentences("Really? Yes! Exactly.")
        assert len(result) == 1

    def test_empty_string(self):
        from tts import _split_sentences

        assert _split_sentences("") == [""]

    def test_no_trailing_split(self):
        from tts import _split_sentences

        result = _split_sentences("Done.")
        assert result == ["Done."]


# ── pi_runner event parsing ───────────────────────────────────────────────


class TestParseEvents:
    def test_valid_ndjson(self):
        from pi_runner import _parse_events

        line = json.dumps({"type": "session", "id": "abc"})
        assert _parse_events(line) == [{"type": "session", "id": "abc"}]

    def test_skips_invalid_json(self):
        from pi_runner import _parse_events

        events = _parse_events('not json\n{"type": "session"}')
        assert events == [{"type": "session"}]

    def test_skips_non_dict(self):
        from pi_runner import _parse_events

        assert _parse_events("[1, 2, 3]") == []

    def test_multiple_lines(self):
        from pi_runner import _parse_events

        lines = "\n".join(
            [
                json.dumps({"type": "session", "id": "x"}),
                json.dumps({"type": "agent_start"}),
            ]
        )
        assert len(_parse_events(lines)) == 2


class TestFindSessionId:
    def test_found(self):
        from pi_runner import _find_session_id

        assert _find_session_id([{"type": "session", "id": "abc-123"}]) == "abc-123"

    def test_not_found(self):
        from pi_runner import _find_session_id

        assert _find_session_id([{"type": "agent_start"}]) is None

    def test_empty(self):
        from pi_runner import _find_session_id

        assert _find_session_id([]) is None

    def test_id_must_be_string(self):
        from pi_runner import _find_session_id

        assert _find_session_id([{"type": "session", "id": 123}]) is None


def _agent_end(messages: list[dict], *, will_retry: bool = False) -> dict:
    ev: dict = {"type": "agent_end", "messages": messages}
    if will_retry:
        ev["willRetry"] = True
    return ev


def _assistant_msg(*blocks: dict) -> dict:
    return {"role": "assistant", "content": list(blocks)}


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def _thinking_block(thinking: str) -> dict:
    return {"type": "thinking", "thinking": thinking, "thinkingSignature": "sig"}


class TestExtractText:
    def test_extracts_text_from_agent_end(self):
        from pi_runner import _extract_text

        events = [_agent_end([_assistant_msg(_text_block("Hello there."))])]
        assert _extract_text(events) == "Hello there."

    def test_empty_events(self):
        from pi_runner import _extract_text

        assert _extract_text([]) == ""

    def test_excludes_thinking_blocks(self):
        from pi_runner import _extract_text

        events = [
            _agent_end(
                [
                    _assistant_msg(
                        _thinking_block("step 1: think hard"),
                        _text_block("The answer is 42."),
                    )
                ]
            )
        ]
        assert _extract_text(events) == "The answer is 42."

    def test_ignores_will_retry_agent_end(self):
        from pi_runner import _extract_text

        events = [
            _agent_end([_assistant_msg(_text_block("attempt 1"))], will_retry=True),
            _agent_end([_assistant_msg(_text_block("final answer"))]),
        ]
        assert _extract_text(events) == "final answer"

    def test_multiple_text_blocks_joined(self):
        from pi_runner import _extract_text

        events = [
            _agent_end(
                [
                    _assistant_msg(
                        _thinking_block("reasoning..."),
                        _text_block("Part one."),
                        _text_block("Part two."),
                    )
                ]
            )
        ]
        assert _extract_text(events) == "Part one.\nPart two."

    def test_skips_user_messages(self):
        from pi_runner import _extract_text

        events = [
            _agent_end(
                [
                    {"role": "user", "content": [_text_block("user prompt")]},
                    _assistant_msg(_text_block("reply")),
                ]
            )
        ]
        assert _extract_text(events) == "reply"

    def test_no_agent_end_returns_empty(self):
        from pi_runner import _extract_text

        events = [{"type": "agent_start"}, {"type": "turn_start"}]
        assert _extract_text(events) == ""


class TestFindError:
    def test_finds_error(self):
        from pi_runner import _find_error

        events = [{"type": "message", "stopReason": "error", "errorMessage": "oops"}]
        assert _find_error(events) == "oops"

    def test_no_error(self):
        from pi_runner import _find_error

        assert _find_error([{"type": "session", "id": "x"}]) is None

    def test_fallback_message(self):
        from pi_runner import _find_error

        events = [{"type": "message", "stopReason": "error"}]
        assert _find_error(events) == "unknown pi error"


# ── routes.talk helpers ───────────────────────────────────────────────────


class TestTruthy:
    def test_true_values(self):
        from routes.talk import _truthy

        for v in ("true", "True", "1", "yes", "YES"):
            assert _truthy(v), f"Expected truthy: {v!r}"

    def test_false_values(self):
        from routes.talk import _truthy

        for v in ("false", "False", "0", "no", ""):
            assert not _truthy(v), f"Expected falsy: {v!r}"


# ── chats.create_chat validation ──────────────────────────────────────────


class TestCreateChat:
    def test_rejects_absolute_path(self, tmp_path):
        from chats import create_chat

        with patch("chats.DEVELOPER_DIR", tmp_path):
            with pytest.raises(ValueError):
                create_chat("/etc/passwd")

    def test_rejects_parent_traversal(self, tmp_path):
        from chats import create_chat

        with patch("chats.DEVELOPER_DIR", tmp_path):
            with pytest.raises(ValueError):
                create_chat("../outside")

    def test_rejects_nonexistent_dir(self, tmp_path):
        from chats import create_chat

        with patch("chats.DEVELOPER_DIR", tmp_path):
            with pytest.raises(ValueError):
                create_chat("doesnotexist")

    def test_valid_dir(self, tmp_path):
        from chats import create_chat

        (tmp_path / "myproject").mkdir()
        with patch("chats.DEVELOPER_DIR", tmp_path), patch("chats.save_chats", lambda: None):
            chat = create_chat("myproject")
        assert chat.project_dir == "myproject"
        assert chat.id


# ── PI_BIN runtime checks ─────────────────────────────────────────────────────


class TestPiBinRuntime:
    """These tests exercise the real pi binary — they fail if pi is missing or
    if the subprocess PATH is wrong (the launchd exit-127 failure mode)."""

    def test_pi_bin_is_not_none(self):
        from config import PI_BIN

        assert PI_BIN is not None, "PI_BIN is None — pi not found via shutil.which"

    def test_pi_bin_is_executable(self):
        import os

        from config import PI_BIN

        assert PI_BIN is not None
        assert os.path.isfile(PI_BIN), f"PI_BIN path does not exist: {PI_BIN}"
        assert os.access(PI_BIN, os.X_OK), f"PI_BIN is not executable: {PI_BIN}"

    def test_pi_bin_runs_with_augmented_path(self):
        """Verify that pi can actually execute with the PATH the server injects.

        This is the exact failure mode that caused exit code 127 in production:
        pi is a Node script (`#!/usr/bin/env node`) and the launchd PATH
        didn't include /opt/homebrew/bin so `env node` couldn't find node.
        """
        import os
        import subprocess

        from config import PI_BIN

        assert PI_BIN is not None
        existing_path = os.environ.get("PATH", "")
        extra = "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin"
        augmented_path = f"{extra}:{existing_path}" if existing_path else extra
        env = {**os.environ, "PATH": augmented_path}

        # pi --help exits 0 and writes to stdout without needing a project
        result = subprocess.run(
            [PI_BIN, "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert result.returncode == 0, (
            f"pi exited {result.returncode} with augmented PATH.\n"
            f"stderr: {result.stderr[:500]}\n"
            f"This is the exit-127 bug: node not in PATH={augmented_path!r}"
        )

    def test_pi_bin_exits_nonzero_without_augmented_path(self):
        """Document the failure: pi exits 127 without Homebrew in PATH.

        This test is informational — it confirms the bug existed and the fix
        is necessary. If this test starts PASSING (pi works even with a bare
        PATH), the path augmentation in pi_runner.py is still harmless.
        """
        import os
        import subprocess

        from config import PI_BIN

        if PI_BIN is None:
            pytest.skip("PI_BIN not set")

        bare_path = "/usr/bin:/bin:/usr/sbin:/sbin"
        env = {**os.environ, "PATH": bare_path}
        result = subprocess.run(
            [PI_BIN, "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        # 127 = node not found, 1 = some other error — either way not 0
        if result.returncode == 0:
            pytest.skip("pi works even with bare PATH (node must be in a system location)")
        assert result.returncode != 0, "expected failure without Homebrew in PATH"


# ── load_chats in-place mutation test ────────────────────────────────────────


class TestLoadChatsInPlace:
    """Regression for the production-only bug where load_chats() rebinds _chats
    but route modules that did `from chats import _chats` still hold the old ref."""

    def test_load_chats_does_not_rebind_reference(self, tmp_path):
        import json

        import chats as chats_mod

        # Capture the identity of the dict BEFORE load_chats is called
        original_id = id(chats_mod._chats)
        ref_before = chats_mod._chats  # simulates what route modules do

        chats_file = tmp_path / "chats.json"
        chats_file.write_text(json.dumps({"chats": {}}))

        from unittest.mock import patch

        with patch.object(chats_mod, "CHATS_FILE", chats_file):
            chats_mod.load_chats()

        # Dict must be the same object — route modules still see the same ref
        assert id(chats_mod._chats) == original_id, (
            "load_chats() rebound _chats to a new object — "
            "route modules with `from chats import _chats` will see the OLD empty dict"
        )
        assert chats_mod._chats is ref_before

    def test_chats_loaded_from_disk_visible_via_captured_reference(self, tmp_path):
        """After load_chats(), a reference captured before the call sees the new chats."""
        import json
        from dataclasses import asdict

        import chats as chats_mod

        # Simulate a chat on disk
        existing = chats_mod.Chat(id="abc123", name="test", project_dir="test")
        chats_file = tmp_path / "chats.json"
        chats_file.write_text(json.dumps({"chats": {"abc123": asdict(existing)}}))

        # Capture reference before calling load_chats (what routes do at import time)
        ref = chats_mod._chats

        from unittest.mock import patch

        with patch.object(chats_mod, "CHATS_FILE", chats_file):
            chats_mod.load_chats()

        # The captured reference must see the loaded chat
        assert "abc123" in ref, (
            "Captured reference doesn't see loaded chats — "
            "load_chats() likely rebound _chats instead of updating in-place"
        )


# ── pi_runner command-line construction ───────────────────────────────────────


class TestPiCommandLine:
    """Tests that the pi subprocess command line is built correctly.

    We run_pi with a real-looking Chat and inspect the cmd list passed to
    subprocess.run, which we intercept with a mock.
    """

    def _run_and_capture_cmd(self, chat, *, model="", save_path="docs/patchbay/"):
        """Call run_pi and return the cmd list from the mocked subprocess.run."""
        import sys
        from unittest.mock import patch

        from chats import save_chats
        from pi_runner import run_pi

        captured = {}

        def _fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            # Return something that looks like a valid CompletedProcess
            import subprocess
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='{"type":"session","id":"sess-1"}\n{"type":"agent_end","messages":[{"role":"assistant","content":[{"type":"text","text":"ok"}]}]}', stderr="")

        with (
            patch("pi_runner.subprocess.run", side_effect=_fake_run),
            patch("pi_runner.save_chats", lambda: None),
        ):
            try:
                import asyncio
                asyncio.run(run_pi("hello", chat, save_path=save_path, model=model))
            except Exception as exc:
                # If the test fails elsewhere we still have the cmd
                if "cmd" not in captured:
                    raise exc
        return captured.get("cmd", [])

    def test_uses_configured_model_by_default(self):
        from chats import Chat

        chat = Chat(id="t1", name="test", project_dir="proj")
        cmd = self._run_and_capture_cmd(chat)
        # --model ... should be present and not empty
        model_idx = cmd.index("--model") if "--model" in cmd else -1
        assert model_idx >= 0, f"--model not found in cmd: {cmd}"
        assert cmd[model_idx + 1] is not None
        assert len(cmd[model_idx + 1]) > 0

    def test_requested_model_appears_in_command_line(self):
        from chats import Chat

        chat = Chat(id="t2", name="test", project_dir="proj")
        cmd = self._run_and_capture_cmd(chat, model="gpt-4o")
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "gpt-4o", f"Expected gpt-4o, got {cmd[model_idx + 1]}"

    def test_includes_lockdown_flags(self):
        from chats import Chat

        chat = Chat(id="t3", name="test", project_dir="proj")
        cmd = self._run_and_capture_cmd(chat)
        cmd_str = " ".join(cmd)
        assert "--no-builtin-tools" in cmd_str, f"Missing --no-builtin-tools in {cmd}"
        assert "--no-extensions" in cmd_str, f"Missing --no-extensions in {cmd}"
        assert "--no-skills" in cmd_str, f"Missing --no-skills in {cmd}"

    def test_includes_extension_path(self):
        from chats import Chat

        chat = Chat(id="t4", name="test", project_dir="proj")
        cmd = self._run_and_capture_cmd(chat)
        ext_idx = cmd.index("--extension") if "--extension" in cmd else -1
        assert ext_idx >= 0, f"--extension not found in cmd: {cmd}"
        assert cmd[ext_idx + 1].endswith("tools.ts")

    def test_includes_session_id_when_present(self):
        from chats import Chat

        chat = Chat(id="t5", name="test", project_dir="proj", pi_session_id="sess-x")
        cmd = self._run_and_capture_cmd(chat)
        sess_idx = cmd.index("--session") if "--session" in cmd else -1
        assert sess_idx >= 0, f"--session not found in cmd: {cmd}"
        assert cmd[sess_idx + 1] == "sess-x"

    def test_omits_session_id_when_none(self):
        from chats import Chat

        chat = Chat(id="t6", name="test", project_dir="proj", pi_session_id=None)
        cmd = self._run_and_capture_cmd(chat)
        assert "--session" not in cmd, f"--session should not be in cmd: {cmd}"


# ── pi_runner PI_BIN None check ──────────────────────────────────────────────


class TestPiBinNone:
    def test_raises_500_with_clear_message(self):
        """When PI_BIN is None, run_pi should fail fast with a helpful message."""
        from unittest.mock import patch

        from chats import Chat
        from pi_runner import run_pi

        chat = Chat(id="x1", name="test", project_dir="proj")

        with (
            patch("pi_runner.PI_BIN", None),
            patch("pi_runner.save_chats", lambda: None),
        ):
            import asyncio

            with pytest.raises(Exception) as exc_info:
                asyncio.run(run_pi("hello", chat))

        # Should be an HTTPException with status 500
        from fastapi import HTTPException

        assert isinstance(exc_info.value, HTTPException), f"Expected HTTPException, got {type(exc_info.value)}"
        assert exc_info.value.status_code == 500
        assert "pi binary not found" in exc_info.value.detail.lower()


# ── chat_json includes pi_session_id ─────────────────────────────────────────


class TestChatJson:
    def test_includes_pi_session_id(self):
        from chats import Chat, chat_json

        chat = Chat(id="cj1", name="test", project_dir="proj", pi_session_id="sess-abc")
        j = chat_json(chat)
        assert j["pi_session_id"] == "sess-abc"

    def test_pi_session_id_is_none_by_default(self):
        from chats import Chat, chat_json

        chat = Chat(id="cj2", name="test", project_dir="proj")
        j = chat_json(chat)
        assert j["pi_session_id"] is None


# ── chat_json save_chats atomic write ────────────────────────────────────────


class TestSaveChatsAtomic:
    def test_writes_to_temp_file_then_replaces(self, tmp_path):
        """save_chats should write to a temp file first, then os.replace."""
        import json
        from unittest.mock import patch

        import chats as chats_mod

        chat = chats_mod.Chat(id="a1", name="test", project_dir="proj")
        chats_mod._chats[chat.id] = chat

        chats_file = tmp_path / "voice-chats.json"
        with patch.object(chats_mod, "CHATS_FILE", chats_file):
            chats_mod.save_chats()

        assert chats_file.exists(), f"File was not created: {chats_file}"
        data = json.loads(chats_file.read_text())
        assert "a1" in data["chats"]

    def test_corrupt_file_recovers_on_next_write(self, tmp_path):
        """A corrupted file should not prevent subsequent saves."""
        import json
        from unittest.mock import patch

        import chats as chats_mod

        chats_file = tmp_path / "voice-chats.json"
        chats_file.write_text("{garbage}")  # corrupt

        chat = chats_mod.Chat(id="b1", name="test", project_dir="proj")
        chats_mod._chats[chat.id] = chat

        with patch.object(chats_mod, "CHATS_FILE", chats_file):
            chats_mod.save_chats()

        # The file should now be valid JSON
        data = json.loads(chats_file.read_text())
        assert "b1" in data["chats"]


# ── Audio MIME types ─────────────────────────────────────────────────────────


class TestAudioMime:
    def test_mp3_returns_audio_mpeg(self, client, tmp_path):
        """MP3 files from Google TTS must be served as audio/mpeg."""
        from config import AUDIO_DIR
        from unittest.mock import patch

        mp3 = tmp_path / "test.mp3"
        mp3.write_bytes(b"fake mp3")

        with patch("routes.misc.AUDIO_DIR", tmp_path):
            r = client.get("/audio/test.mp3")
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/mpeg"

    def test_m4a_returns_audio_mp4(self, client, tmp_path):
        from config import AUDIO_DIR
        from unittest.mock import patch

        m4a = tmp_path / "test.m4a"
        m4a.write_bytes(b"fake m4a")

        with patch("routes.misc.AUDIO_DIR", tmp_path):
            r = client.get("/audio/test.m4a")
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/mp4"

    def test_unknown_extension_returns_octet_stream(self, client, tmp_path):
        from config import AUDIO_DIR
        from unittest.mock import patch

        unknown = tmp_path / "test.wav"
        unknown.write_bytes(b"fake wav")

        with patch("routes.misc.AUDIO_DIR", tmp_path):
            r = client.get("/audio/test.wav")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/octet-stream"

    def test_serves_static_fallback_clip_from_assets_dir(self, client, tmp_path):
        """The static TTS-unavailable clip lives in ASSETS_DIR, not AUDIO_DIR —
        /audio/{name} must still be able to serve it, or audio_degraded turns
        would report success while the actual audio 404s."""
        from unittest.mock import patch

        empty_audio_dir = tmp_path / "audio"
        empty_audio_dir.mkdir()
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        clip = assets_dir / "audio-unavailable.m4a"
        clip.write_bytes(b"fake clip")

        with patch("routes.misc.AUDIO_DIR", empty_audio_dir), patch("routes.misc.ASSETS_DIR", assets_dir):
            r = client.get("/audio/audio-unavailable.m4a")
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/mp4"

    def test_still_404s_when_missing_from_both_dirs(self, client, tmp_path):
        from unittest.mock import patch

        with patch("routes.misc.AUDIO_DIR", tmp_path), patch("routes.misc.ASSETS_DIR", tmp_path):
            r = client.get("/audio/nope.mp3")
        assert r.status_code == 404


# ── tts.synthesize fallback chain ─────────────────────────────────────────


class TestTtsFallback:
    """Tests for the one-way TTS fallback chain: Google → local engine → static clip."""

    def test_google_fallback_to_say_succeeds(self, tmp_path):
        """Google failure → falls back to say → returns say path, not degraded."""
        import asyncio

        from unittest.mock import AsyncMock, patch

        import tts as tts_mod

        say_path = tmp_path / "say.m4a"
        say_path.write_bytes(b"say audio")

        with (
            patch("tts._google_tts", side_effect=RuntimeError("google down")),
            patch("tts._local_tts", new_callable=AsyncMock, return_value=say_path),
        ):
            path, degraded = asyncio.run(tts_mod.synthesize("hello", provider="google"))

        assert path == say_path
        assert not degraded

    def test_google_and_say_both_fail_returns_static(self, tmp_path):
        """Google failure → say also fails → returns static clip path, degraded."""
        import asyncio

        from unittest.mock import AsyncMock, patch

        import tts as tts_mod

        with (
            patch("tts._google_tts", side_effect=RuntimeError("google down")),
            patch("tts._local_tts", side_effect=RuntimeError("say not available")),
        ):
            path, degraded = asyncio.run(tts_mod.synthesize("hello", provider="google"))

        assert path == tts_mod._STATIC_FALLBACK
        assert degraded

    def test_say_failure_does_not_call_google(self, tmp_path):
        """Say (as primary) failure → static clip directly, NEVER calls _google_tts."""
        import asyncio

        from unittest.mock import AsyncMock, patch

        import tts as tts_mod

        google_mock = AsyncMock()
        with (
            patch("tts._local_tts", side_effect=RuntimeError("say not available")),
            patch("tts._google_tts", google_mock),
        ):
            path, degraded = asyncio.run(tts_mod.synthesize("hello", provider="say"))

        assert path == tts_mod._STATIC_FALLBACK
        assert degraded
        google_mock.assert_not_called()

    def test_say_normal_no_degradation(self, tmp_path):
        """Say works normally — not degraded, returns say path."""
        import asyncio

        from unittest.mock import AsyncMock, patch

        import tts as tts_mod

        say_path = tmp_path / "say.m4a"
        say_path.write_bytes(b"say audio")

        with patch("tts._local_tts", new_callable=AsyncMock, return_value=say_path):
            path, degraded = asyncio.run(tts_mod.synthesize("hello", provider="say"))

        assert path == say_path
        assert not degraded

    def test_google_normal_no_degradation(self, tmp_path):
        """Google works normally — not degraded, returns google path."""
        import asyncio

        from unittest.mock import AsyncMock, patch

        import tts as tts_mod

        google_path = tmp_path / "out.mp3"
        google_path.write_bytes(b"google audio")

        with patch("tts._google_tts", new_callable=AsyncMock, return_value=google_path):
            path, degraded = asyncio.run(tts_mod.synthesize("hello", provider="google"))

        assert path == google_path
        assert not degraded

    def test_multi_chunk_one_chunk_falls_back_to_say(self, tmp_path):
        """Multi-chunk: first chunk's Google fails, falls back to say; other chunks fine."""
        import asyncio

        from unittest.mock import patch

        import tts as tts_mod

        say_path = tmp_path / "say.m4a"
        say_path.write_bytes(b"say")
        google_success = tmp_path / "google.mp3"
        google_success.write_bytes(b"google")

        call_count = 0

        async def mock_google(text, speaking_rate=1.0):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("google down for first chunk")
            return google_success

        with (
            patch("tts._split_sentences", return_value=["First.", "Second.", "Third."]),
            patch("tts._google_tts", mock_google),
            patch("tts._local_tts", return_value=say_path),
        ):
            paths, any_degraded = asyncio.run(
                tts_mod.synthesize_chunked("First. Second. Third.", provider="google")
            )

        assert len(paths) == 3
        assert paths[0] == say_path  # first chunk fell back to say
        assert paths[1] == google_success
        assert paths[2] == google_success
        # Not degraded overall — the failed chunk successfully fell back to say
        assert not any_degraded

    def test_multi_chunk_one_chunk_both_providers_fail(self, tmp_path):
        """Multi-chunk: one chunk fails both Google and say → static clip for that chunk."""
        import asyncio

        from unittest.mock import patch

        import tts as tts_mod

        google_success = tmp_path / "google.mp3"
        google_success.write_bytes(b"google")

        call_count = 0

        async def mock_google(text, speaking_rate=1.0):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("google down for first chunk")
            return google_success

        with (
            patch("tts._split_sentences", return_value=["First.", "Second.", "Third."]),
            patch("tts._google_tts", mock_google),
            patch("tts._local_tts", side_effect=RuntimeError("say also down")),
        ):
            paths, any_degraded = asyncio.run(
                tts_mod.synthesize_chunked("First. Second. Third.", provider="google")
            )

        assert len(paths) == 3
        assert paths[0] == tts_mod._STATIC_FALLBACK  # both failed → static clip
        assert paths[1] == google_success
        assert paths[2] == google_success
        assert any_degraded
