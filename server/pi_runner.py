from __future__ import annotations

import asyncio
import json
import subprocess
import sys

from fastapi import HTTPException

from chats import Chat, save_chats
from config import EXTENSION_PATH, PI_BIN, PI_MODEL, PI_PROVIDER, SYSTEM_PROMPT


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
    project_dir = str(chat.project_dir)

    def _run() -> tuple[str, str, int]:
        cmd = [
            PI_BIN,
            "-p",
            project_dir,
            "--mode",
            "json",
            "--provider",
            PI_PROVIDER,
            "--model",
            PI_MODEL,
        ]
        if chat.pi_session_id:
            cmd.extend(["--session", chat.pi_session_id])
        cmd.extend(["--append-system-prompt", str(SYSTEM_PROMPT)])
        cmd.extend(["--no-builtin-tools"])
        cmd.extend(["--extension", str(EXTENSION_PATH)])
        cmd.append(user_text)

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode

    stdout, stderr, rc = await asyncio.to_thread(_run)
    events = _parse_events(stdout)

    new_sid = _find_session_id(events)
    if new_sid:
        chat.pi_session_id = new_sid
        save_chats()

    err = _find_error(events)
    if err:
        print(f"[pi] error: {err}", file=sys.stderr)
        raise HTTPException(500, f"pi error: {err}")

    if rc != 0:
        print(f"[pi] error: {stderr}", file=sys.stderr)
        raise HTTPException(500, f"pi exited {rc}: {stderr}")

    text = _extract_text(events)
    return text or "(no response)"
