from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    yield


app = FastAPI(title="voice-demo", lifespan=lifespan)
app.include_router(talk_router)
app.include_router(chats_router)
app.include_router(misc_router)
