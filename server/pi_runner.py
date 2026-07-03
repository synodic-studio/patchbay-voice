from __future__ import annotations

import asyncio
import json
import subprocess
import sys

from fastapi import HTTPException

from chats import Chat, save_chats
from config import DEVELOPER_DIR, EXTENSION_PATH, PI_BIN, PI_MODEL, PI_PROVIDER

PI_TIMEOUT = 120  # seconds


BASE_SYSTEM_PROMPT = (
    "You are a voice coding assistant accessed from a mobile phone. The user speaks to you "
    "and your replies are read aloud by text-to-speech. Follow these rules strictly at all times:\n\n"
    "Speak in plain English only. Never use markdown, headings, bullet points, numbered lists, "
    "code blocks, backticks, bold, italics, URLs, or any other formatting meant for visual reading. "
    "Write exactly as you would speak to someone on a phone call.\n\n"
    "Keep answers short and conversational. One to three sentences unless the user clearly needs "
    "more. When referring to code, describe it in plain words rather than quoting syntax.\n\n"
    "Compose your entire reply before delivering it. Give one complete spoken response per turn "
    "— not a series of chunks, sections, or partial thoughts.\n\n"
    "The write_file tool is for saving notes, plans, and anything the user asks you to record "
    "— for future reference and posterity, not for communicating information in the current "
    "conversation. If you have something to say, say it in your reply. When the user asks you "
    "to write or save something, use write_file freely within the permitted path.\n\n"
    "The tools available to you were chosen deliberately.\n\n"
    "* Do not attempt to work around their restrictions\n"
    "* Do not chain tool calls to escape the {save_path} write boundary\n"
    "* Do not modify, delete, or rename files outside {save_path}\n"
    "* Do not use git tools to stage, commit, or push changes\n"
    "* Do not proactively create documents to convey information — speak instead\n"
    "* Do not look for workarounds when a restriction blocks you — explain what you cannot do instead"
)


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
    for ev in reversed(events):
        if ev.get("type") != "agent_end" or ev.get("willRetry"):
            continue
        parts: list[str] = []
        for msg in ev.get("messages", []):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "")
                        if text:
                            parts.append(text)
        if parts:
            return "\n".join(parts).strip()
    return ""


def _find_error(events: list[dict]) -> str | None:
    for msg in events:
        if msg.get("type") == "message" and msg.get("stopReason") == "error":
            return msg.get("errorMessage", "unknown pi error")
    return None


async def run_pi(user_text: str, chat: Chat, *, save_path: str = "docs/patchbay/", model: str = "") -> str:
    # Fail fast if pi isn't installed — don't let None propagate to subprocess
    if PI_BIN is None:
        raise HTTPException(
            500,
            "pi binary not found on PATH — install pi or set PI_BIN",
        )

    cwd = str(DEVELOPER_DIR / chat.project_dir)
    # pi doesn't support -- terminator; guard against flag-like input from ASR
    safe_text = (" " + user_text) if user_text.startswith("-") else user_text

    # Build the system prompt with the actual save path so the write boundary
    # matches what the server and extension use.
    system_prompt = BASE_SYSTEM_PROMPT.replace("{save_path}", save_path)

    def _run() -> tuple[str, str, int]:
        import os

        # Launchd gives us PATH=/usr/bin:/bin only. pi is a Node script so
        # `env node` must find node — prepend Homebrew and local bin.
        existing_path = os.environ.get("PATH", "")
        extra = "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin"
        augmented_path = f"{extra}:{existing_path}" if existing_path else extra
        env = {**os.environ, "VOICE_SAVE_PATH": save_path, "PATH": augmented_path}
        cmd = [
            PI_BIN,
            "-p",  # --print: non-interactive, process prompt and exit
            "--mode",
            "json",
            "--provider",
            PI_PROVIDER,
        ]
        # Thread the requested model (or fall back to the configured default)
        active_model = model if model else PI_MODEL
        cmd.extend(["--model", active_model])

        if chat.pi_session_id:
            cmd.extend(["--session", chat.pi_session_id])
        cmd.extend(["--append-system-prompt", system_prompt])
        # Lock down: no built-in tools, no global extensions, no skills
        cmd.extend(["--no-builtin-tools"])
        cmd.extend(["--no-extensions"])
        cmd.extend(["--no-skills"])
        cmd.extend(["--extension", str(EXTENSION_PATH)])
        cmd.append(safe_text)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env, timeout=PI_TIMEOUT)
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
