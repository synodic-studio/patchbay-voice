"""Production app with observation-only hooks and isolated pi session files.
Run through uv from server; VIDEO_RUN_DIR points at the capture's private directory.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'server'))
import routes.talk as talk
from app import app

RUN = Path(os.environ['VIDEO_RUN_DIR'])
RUN.mkdir(parents=True, exist_ok=True)
original_run_pi = talk.run_pi
original_log = talk._log_stage


def emit(kind, payload):
    with (RUN / 'events.jsonl').open('a') as file:
        file.write(json.dumps({'time': time.time(), 'kind': kind, **payload}) + '\n')


def observed_stage(chat_id, stage, detail=''):
    emit('stage', {'chat_id': chat_id, 'stage': stage, 'detail': detail})
    original_log(chat_id, stage, detail)


async def observed_pi(text, chat, **kwargs):
    def event(value):
        # Retain public tool evidence; never persist model reasoning blocks.
        if value.get('type') in ('tool_execution_start', 'tool_execution_end'):
            emit('tool', {'event': value})
    return await original_run_pi(text, chat, on_event=event,
                                 session_dir=RUN / 'pi-sessions', **kwargs)


talk.run_pi = observed_pi
talk._log_stage = observed_stage

@app.middleware("http")
async def capture_response(request, call_next):
    if request.url.path != "/api/talk":
        return await call_next(request)
    response = await call_next(request)
    body = b"".join([chunk async for chunk in response.body_iterator])
    from starlette.responses import Response
    if response.status_code == 200:
        data = json.loads(body)
        index = len(list(RUN.glob("response-*.json")))
        (RUN / f"response-{index}.json").write_text(json.dumps(data, indent=2))
        emit("response", {"index": index, "response": data})
        if not data.get("failed"):
            (RUN / f"turn-{index}-done").touch()
    return Response(body, status_code=response.status_code, headers=dict(response.headers),
                    media_type=response.media_type)
