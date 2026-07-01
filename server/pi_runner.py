from __future__ import annotations

import asyncio
import json
import subprocess
import sys

from fastapi import HTTPException

from chats import Chat, save_chats
from config import DEVELOPER_DIR, EXTENSION_PATH, PI_BIN, PI_MODEL, PI_PROVIDER, SYSTEM_PROMPT

PI_TIMEOUT = 120  # seconds


def _parse_events(stdout: str) -> list[dict]:
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                events.append(obj)
        except json.JSONDecodeError:
            pass
    return events


def _find_session_id(events: list[dict]) -> str | None:
    for msg in events:
        if msg.get("type") == "session" and isinstance(msg.get("id"), str):
            return msg["id"]
    return None


def _extract_text(events: list[dict]) -> str:
    for msg in reversed(events):
        if msg.get("type") == "agent_end":
            parts = []
            for block in msg.get("messages", []):
                if block.get("role") == "assistant":
                    parts.extend(b.get("text", "") for b in block.get("content", []) if b.get("text"))
            return "\n".join(parts).strip()
    return ""


def _find_error(events: list[dict]) -> str | None:
    for msg in events:
        if msg.get("type") == "message" and msg.get("stopReason") == "error":
            return msg.get("errorMessage", "unknown pi error")
    return None


async def run_pi(user_text: str, chat: Chat) -> str:
    cwd = str(DEVELOPER_DIR / chat.project_dir)
    # pi doesn't support -- terminator; guard against flag-like input from ASR
    safe_text = (" " + user_text) if user_text.startswith("-") else user_text

    def _run() -> tuple[str, str, int]:
        cmd = [
            PI_BIN,
            "-p",  # --print: non-interactive, process prompt and exit
            "--mode",
            "json",
            "--provider",
            PI_PROVIDER,
            "--model",
            PI_MODEL,
        ]
        if chat.pi_session_id:
            cmd.extend(["--session", chat.pi_session_id])
        cmd.extend(["--append-system-prompt", SYSTEM_PROMPT])
        cmd.extend(["--no-builtin-tools"])
        cmd.extend(["--extension", str(EXTENSION_PATH)])
        cmd.append(safe_text)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=PI_TIMEOUT)
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            print(f"[pi] timeout after {PI_TIMEOUT}s chat={chat.id}", file=sys.stderr)
            raise HTTPException(504, f"pi timed out after {PI_TIMEOUT}s")

    stdout, stderr, rc = await asyncio.to_thread(_run)

    if rc != 0 or stderr:
        print(f"[pi] rc={rc} chat={chat.id} cwd={cwd}", file=sys.stderr)
        if stderr:
            print(f"[pi] stderr: {stderr[:2000]}", file=sys.stderr)
        if stdout:
            print(f"[pi] stdout: {stdout[:500]}", file=sys.stderr)

    events = _parse_events(stdout)

    new_sid = _find_session_id(events)
    if new_sid:
        chat.pi_session_id = new_sid
        save_chats()

    err = _find_error(events)
    if err:
        raise HTTPException(500, f"pi error: {err}")

    if rc != 0:
        raise HTTPException(500, f"pi exited {rc}: {stderr[:200]}")

    text = _extract_text(events)
    return text or "(no response)"
