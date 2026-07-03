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


def _msg_update(kind: str, content: str, idx: int = 0) -> dict:
    """Build a message_update event as pi emits."""
    ame: dict = {"type": kind, "contentIndex": idx}
    if kind == "text_delta":
        ame["delta"] = content
    elif kind == "text_end":
        ame["content"] = content
    return {"type": "message_update", "assistantMessageEvent": ame}


class TestExtractText:
    def test_extracts_text_end(self):
        from pi_runner import _extract_text

        events = [_msg_update("text_end", "Hello there.")]
        assert _extract_text(events) == "Hello there."

    def test_empty_events(self):
        from pi_runner import _extract_text

        assert _extract_text([]) == ""

    def test_accumulates_deltas_when_no_text_end(self):
        from pi_runner import _extract_text

        events = [
            _msg_update("text_delta", "Hello "),
            _msg_update("text_delta", "there."),
        ]
        assert _extract_text(events) == "Hello there."

    def test_prefers_text_end_over_deltas(self):
        from pi_runner import _extract_text

        events = [
            _msg_update("text_delta", "partial"),
            _msg_update("text_end", "Hello there."),
        ]
        assert _extract_text(events) == "Hello there."

    def test_multiple_content_blocks(self):
        from pi_runner import _extract_text

        events = [
            _msg_update("text_end", "first", idx=0),
            _msg_update("text_end", "second", idx=1),
        ]
        assert _extract_text(events) == "first\nsecond"

    def test_ignores_non_message_update_events(self):
        from pi_runner import _extract_text

        events = [
            {"type": "agent_end", "messages": [{"role": "assistant", "content": [{"text": "ignored"}]}]},
            _msg_update("text_end", "kept"),
        ]
        assert _extract_text(events) == "kept"


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
