#!/usr/bin/env python3
"""
Generate Google TTS narration and mix it into the walkthrough video.

Usage:
    uv run --with google-auth --with httpx --with requests python3 /private/tmp/narrate.py \
        --video /path/to/raw.mp4 --out /path/to/final.mp4

The script fetches a service-account token from pass, calls the Google TTS
REST API for each narration line, builds a single audio track with adelay,
then mixes that track into the video.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import subprocess
import tempfile
from pathlib import Path

import httpx

VOICE = "en-US-Chirp3-HD-Schedar"
SPEAKING_RATE = 0.92

# Raw recording is trimmed at 16s to remove home-screen overhead.
# These timestamps are relative to the trimmed video:
#   0s    talk screen appears (2 existing turns)
#   6.5s  sessions sheet opens
#   10.5s back on talk screen
#   15s   red mic (hold starts)
#   17s   Thinking… bubble
#   19s   3rd turn appears
#   24s   settings sheet
LINES: list[tuple[int, str]] = [
    (400, "Patchbay Voice. Talk to Claude Code from your phone."),
    (6500, "Sessions are scoped to repos. Each project keeps its own context."),
    (11000, "Previous turns load instantly."),
    (13500, "Hold the mic to record."),
    (15500, "Release to send."),
    (17500, "Claude transcribes, responds, and the reply appears right here."),
    (24000, "Settings: server, model, voice, and write directory."),
]

# Minimum silence gap enforced between consecutive clips (ms)
MIN_GAP_MS = 350

# Trim offset (seconds) cut from the start of raw video
TRIM_OFFSET_S = 16


def _get_google_token() -> str:
    sa_json = subprocess.check_output(["pass", "show", "google-tts-service-account"], text=True).strip()
    import google.auth.transport.requests
    import google.oauth2.service_account

    creds = google.oauth2.service_account.Credentials.from_service_account_info(
        json.loads(sa_json),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


async def _tts_line(client: httpx.AsyncClient, token: str, text: str, path: Path) -> None:
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": VOICE},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": SPEAKING_RATE},
    }
    resp = await client.post(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    path.write_bytes(base64.b64decode(resp.json()["audioContent"]))
    print(f"  tts → {path.name}")


def _clip_duration_ms(path: Path) -> int:
    out = subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        text=True,
    ).strip()
    return int(float(out) * 1000)


def _schedule(desired: list[tuple[int, Path]]) -> list[tuple[int, Path]]:
    """Push start times forward as needed so no clip overlaps the previous one."""
    result = []
    cursor = 0
    for desired_ms, path in desired:
        start = max(desired_ms, cursor)
        dur = _clip_duration_ms(path)
        cursor = start + dur + MIN_GAP_MS
        result.append((start, path))
        print(f"  sched {path.name}: desired={desired_ms}ms actual={start}ms dur={dur}ms")
    return result


async def generate_all(tmp: Path) -> list[tuple[int, Path]]:
    token = _get_google_token()
    async with httpx.AsyncClient() as client:
        tasks = []
        paths = []
        for i, (ms, text) in enumerate(LINES):
            p = tmp / f"line_{i:02d}.mp3"
            paths.append((ms, p))
            tasks.append(_tts_line(client, token, text, p))
        await asyncio.gather(*tasks)
    return _schedule(paths)


def build_narration_track(segments: list[tuple[int, Path]], out: Path) -> None:
    """Combine MP3 segments with adelay into a single audio track."""
    inputs = []
    filter_parts = []
    mix_inputs = []

    for i, (ms, mp3) in enumerate(segments):
        inputs += ["-i", str(mp3)]
        # stereo adelay: delay both channels by ms milliseconds
        filter_parts.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
        mix_inputs.append(f"[a{i}]")

    n = len(segments)
    filter_complex = ";".join(filter_parts) + f";{''.join(mix_inputs)}amix=inputs={n}:duration=longest[aout]"

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[aout]",
        "-ar",
        "44100",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  narration track → {out}")


def trim_and_convert(raw: Path, out: Path, trim_s: int) -> None:
    """Trim leading overhead and encode to web-safe H.264."""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(trim_s),
        "-i",
        str(raw),
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "slow",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-an",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  trimmed video → {out}")


def mix_into_video(video: Path, audio: Path, out: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    size = out.stat().st_size // 1024
    print(f"  final video → {out}  ({size} KB)")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    video = Path(args.video)
    out = Path(args.out)

    with tempfile.TemporaryDirectory(prefix="pv-narr-") as tmp_str:
        tmp = Path(tmp_str)
        print(f"Trimming video at {TRIM_OFFSET_S}s and converting...")
        trimmed = tmp / "trimmed.mp4"
        trim_and_convert(video, trimmed, TRIM_OFFSET_S)
        print("Generating TTS lines...")
        segments = await generate_all(tmp)
        print("Building narration track...")
        track = tmp / "narration.mp3"
        build_narration_track(segments, track)
        print("Mixing into video...")
        mix_into_video(trimmed, track, out)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
