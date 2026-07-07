"""Regression tests for the auto-commit / auto-push feature and the local
TTS engine dispatch — the pieces that shipped without automated coverage.

The auto-push tests run real git against throwaway repos and a bare remote,
so they exercise the actual commit-tree / update-ref / push path end to end.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

import tts as tts_mod
from routes.chats import _git_capability
from routes.talk import _git_commit, _git_push


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    ).stdout.strip()


def _make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    (path / "README.md").write_text("# repo\n")
    _git(path, "add", "-A")
    _git(path, "commit", "-qm", "init")
    return path


class TestGitCapability:
    """The toggle-gating check: what auto-commit/push can actually do."""

    def test_non_repo_disables_both(self, tmp_path):
        (tmp_path / "plain").mkdir()
        with patch("routes.chats.DEVELOPER_DIR", tmp_path):
            cap = _git_capability("plain")
        assert cap == {"can_commit": False, "can_push": False}

    def test_repo_without_remote_allows_commit_only(self, tmp_path):
        _make_repo(tmp_path / "repo")
        with patch("routes.chats.DEVELOPER_DIR", tmp_path):
            cap = _git_capability("repo")
        assert cap == {"can_commit": True, "can_push": False}

    def test_repo_with_remote_allows_push(self, tmp_path):
        repo = _make_repo(tmp_path / "repo")
        _git(repo, "remote", "add", "origin", "https://example.com/x.git")
        with patch("routes.chats.DEVELOPER_DIR", tmp_path):
            cap = _git_capability("repo")
        assert cap == {"can_commit": True, "can_push": True}


class TestGitCommit:
    """Auto-commit builds an isolated commit without disturbing the user."""

    def test_commits_save_path_to_branch(self, tmp_path):
        repo = _make_repo(tmp_path / "repo")
        save = repo / "docs" / "patchbay"
        save.mkdir(parents=True)
        (save / "note.md").write_text("saved by voice")

        _git_commit(repo, "docs/patchbay", branch="patchbay")

        assert _git(repo, "rev-parse", "--verify", "refs/heads/patchbay")
        assert _git(repo, "show", "patchbay:docs/patchbay/note.md") == "saved by voice"

    def test_does_not_touch_working_branch_or_index(self, tmp_path):
        repo = _make_repo(tmp_path / "repo")
        start_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        start_head = _git(repo, "rev-parse", "HEAD")
        save = repo / "docs" / "patchbay"
        save.mkdir(parents=True)
        (save / "note.md").write_text("saved by voice")

        _git_commit(repo, "docs/patchbay", branch="patchbay")

        # Still on the same branch, HEAD unmoved, note still merely untracked.
        assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == start_branch
        assert _git(repo, "rev-parse", "HEAD") == start_head
        status = _git(repo, "status", "--porcelain")
        # The save path is still merely untracked (git collapses the dir to
        # "?? docs/"); nothing was staged into the user's real index.
        assert "docs/" in status
        assert status.strip().startswith("??")
        assert not any(line[:2] in ("A ", "M ", "AM") for line in status.splitlines())

    def test_noop_when_nothing_under_save_path(self, tmp_path):
        repo = _make_repo(tmp_path / "repo")
        (repo / "docs" / "patchbay").mkdir(parents=True)  # empty save dir
        _git_commit(repo, "docs/patchbay", branch="patchbay")
        # Branch must not be created for an empty (no-diff) commit.
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/patchbay"],
            cwd=str(repo), capture_output=True, text=True,
        )
        assert result.returncode != 0


class TestGitPush:
    """Auto-push lands the branch on a real remote."""

    def test_pushes_branch_to_bare_remote(self, tmp_path):
        repo = _make_repo(tmp_path / "repo")
        bare = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
        _git(repo, "remote", "add", "origin", str(bare))

        save = repo / "docs" / "patchbay"
        save.mkdir(parents=True)
        (save / "note.md").write_text("pushed by voice")
        _git_commit(repo, "docs/patchbay", branch="patchbay")

        _git_push(repo, "patchbay")

        # The bare remote now has the branch and the file.
        assert _git(bare, "rev-parse", "--verify", "refs/heads/patchbay")
        assert _git(bare, "show", "patchbay:docs/patchbay/note.md") == "pushed by voice"

    def test_no_remote_is_a_safe_noop(self, tmp_path):
        repo = _make_repo(tmp_path / "repo")
        # No remote configured — must not raise.
        _git_push(repo, "patchbay")


class TestPickLocalEngine:
    """Local (no-credentials) TTS engine selection — the middle fallback tier."""

    def test_explicit_override_wins(self):
        with patch("tts.LOCAL_TTS_ENGINE", "espeak"):
            assert tts_mod._pick_local_engine() == "espeak"

    def test_prefers_say_when_present(self):
        with (
            patch("tts.LOCAL_TTS_ENGINE", ""),
            patch("tts.shutil.which", lambda c: "/usr/bin/say" if c == "say" else None),
        ):
            assert tts_mod._pick_local_engine() == "say"

    def test_piper_when_say_absent_and_model_configured(self):
        def which(cmd):
            return None if cmd == "say" else f"/usr/bin/{cmd}"

        with (
            patch("tts.LOCAL_TTS_ENGINE", ""),
            patch("tts.PIPER_MODEL", "/voices/en.onnx"),
            patch("tts.PIPER_BIN", "piper"),
            patch("tts.shutil.which", which),
        ):
            assert tts_mod._pick_local_engine() == "piper"

    def test_espeak_last_resort(self):
        def which(cmd):
            return "/usr/bin/espeak-ng" if cmd == "espeak-ng" else None

        with (
            patch("tts.LOCAL_TTS_ENGINE", ""),
            patch("tts.PIPER_MODEL", ""),
            patch("tts.ESPEAK_BIN", "espeak-ng"),
            patch("tts.shutil.which", which),
        ):
            assert tts_mod._pick_local_engine() == "espeak"

    def test_none_when_nothing_installed(self):
        with (
            patch("tts.LOCAL_TTS_ENGINE", ""),
            patch("tts.PIPER_MODEL", ""),
            patch("tts.shutil.which", lambda c: None),
        ):
            assert tts_mod._pick_local_engine() is None


class TestPiperArgs:
    """piper is coded but the demo box uses espeak, so no live piper run exists.
    Pin its argv construction so a broken invocation can't ship unnoticed."""

    def test_length_scale_is_inverse_of_speaking_rate(self):
        captured = {}

        def fake_run(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs

            class R:
                returncode = 0

            return R()

        with (
            patch("tts.PIPER_MODEL", "/voices/en.onnx"),
            patch("tts.PIPER_BIN", "piper"),
            patch("tts.shutil.which", lambda c: "/usr/bin/piper"),
            patch("tts.subprocess.run", fake_run),
            patch("tts._encode_m4a", lambda src, dst: None),
        ):
            asyncio.run(tts_mod._piper_tts("hello there", speaking_rate=2.0))

        argv = captured["argv"]
        assert argv[0] == "piper"
        assert "--model" in argv and "/voices/en.onnx" in argv
        i = argv.index("--length_scale")
        assert argv[i + 1] == "0.5"  # 1 / 2.0
        assert captured["kwargs"].get("input") == "hello there"


class TestOnDeviceProjects:
    """Projects listed in ONDEVICE_PROJECTS get no server audio, so a capable
    client (the iOS app) speaks the reply with its own on-device voice."""

    def test_ondevice_project_returns_no_server_audio(self, client, chat_id):
        import routes.talk as talk_mod

        async def fake_run_pi(transcript, chat, save_path="", model=""):
            return "This is the spoken reply."

        with (
            patch.object(talk_mod, "run_pi", fake_run_pi),
            patch.object(talk_mod, "ONDEVICE_PROJECTS", {"proj"}),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "true"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["reply"] == "This is the spoken reply."
        assert body["audio_urls"] == []  # no server audio -> app speaks on-device
        assert body["audio_url"] is None

    def test_normal_project_is_unaffected(self, client, chat_id):
        import routes.talk as talk_mod
        import tts as tts_module

        async def fake_run_pi(transcript, chat, save_path="", model=""):
            return "Reply."

        async def fake_synth(text, provider="say", speaking_rate=1.0):
            from config import AUDIO_DIR

            p = AUDIO_DIR / "unit-test.m4a"
            p.write_bytes(b"x")
            return (p, False)

        with (
            patch.object(talk_mod, "run_pi", fake_run_pi),
            patch.object(talk_mod, "ONDEVICE_PROJECTS", set()),
            patch.object(tts_module, "synthesize", fake_synth),
        ):
            r = client.post(
                "/api/talk",
                data={"chat_id": chat_id, "text": "hi", "audio_response": "true"},
            )
        assert r.status_code == 200
        assert r.json()["audio_urls"]  # server produced audio as usual
