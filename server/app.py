from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from chats import _chats, load_chats
from config import CHATS_FILE, HOST, PI_MODEL, PI_PROVIDER, PORT, STATIC_DIR
from routes.chats import router as chats_router
from routes.misc import router as misc_router
from routes.talk import router as talk_router

app = FastAPI(title="voice-demo")
app.include_router(talk_router)
app.include_router(chats_router)
app.include_router(misc_router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup():
    load_chats()
    print(f"[voice-demo] http://{HOST}:{PORT}  pi={PI_PROVIDER}/{PI_MODEL}")
    print(f"[voice-demo] {len(_chats)} chat(s) loaded from {CHATS_FILE}")
