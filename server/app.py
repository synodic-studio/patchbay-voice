from __future__ import annotations

import hmac
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import config
from chats import _chats, load_chats
from config import CHATS_FILE, PI_MODEL, PI_PROVIDER
from routes.chats import router as chats_router
from routes.misc import router as misc_router
from routes.talk import router as talk_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_chats()
    # uvicorn logs its own bind address; we just report what we configured
    print(f"[voice-demo] pi={PI_PROVIDER}/{PI_MODEL}")
    print(f"[voice-demo] {len(_chats)} chat(s) loaded from {CHATS_FILE}")
    if config.AUTH_TOKEN:
        print("[voice-demo] bearer-token auth enabled for /api/*")
    yield


app = FastAPI(title="voice-demo", lifespan=lifespan)


@app.middleware("http")
async def require_bearer_token(request: Request, call_next):
    # Auth only guards the API. GET / (web client) and /audio/* (unguessable
    # UUID filenames, fetched by audio elements that can't send headers) stay open.
    if config.AUTH_TOKEN and request.url.path.startswith("/api/"):
        supplied = request.headers.get("authorization", "")
        expected = f"Bearer {config.AUTH_TOKEN}"
        if not hmac.compare_digest(supplied, expected):
            return JSONResponse(
                {"detail": "missing or invalid bearer token — set the server token in Settings"},
                status_code=401,
            )
    return await call_next(request)


app.include_router(talk_router)
app.include_router(chats_router)
app.include_router(misc_router)
