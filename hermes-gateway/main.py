"""Hermes Office API — thin FastAPI entry point."""
import asyncio
import os
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from src.services.timeline_service import init_sync_db, SYNC_STOP, SYNC_WAKE
from src.api import chat, health, office, profiles, timeline
from src.util.rate_limiter import RateLimitMiddleware

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Hermes Office API", version="2.0.0")

# Rate limiting middleware (before CORS)
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ──────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(office.router)
app.include_router(profiles.router)
app.include_router(timeline.router)


# ── Sync worker ───────────────────────────────────────────────────────────────

def _sync_worker() -> None:
    """Background worker: ingest timeline events from all profiles."""
    from src.services.timeline_service import _sync_worker as _tw
    _tw()


@app.on_event("startup")
def start_sync_worker() -> None:
    init_sync_db()
    SYNC_STOP.clear()
    threading.Thread(target=_sync_worker, daemon=True).start()


@app.on_event("shutdown")
def stop_sync_worker() -> None:
    SYNC_STOP.set()
    SYNC_WAKE.set()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "18100"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
