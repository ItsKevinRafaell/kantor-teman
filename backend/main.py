"""
Kantor Teman API — main entry point.
Thin orchestration layer: middleware, scheduler, router includes.
All business logic lives in app/core/dependencies.py and routers/.
"""
import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv(os.environ.get("ENV_FILE", ".env.production"))

# ── Re-export everything from dependencies for backward compat ─────────────────
from app.core.dependencies import *  # noqa: F401, F403, E402
from app.core.dependencies import (_run_async_job, process_pending_blasts,  # noqa: E402
    scheduled_followup_processor, _acquire_scheduler_lock, _deduct_due_subscriptions,
    _cors_list)

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Kantor Teman API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# ── Middleware ─────────────────────────────────────────────────────────────────

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.middleware("http")
async def query_timing_middleware(request: Request, call_next):
    import time as _time
    start_time = _time.time()
    response = await call_next(request)
    process_time = _time.time() - start_time
    if process_time > 1.0:
        print(f"SLOW REQUEST: {request.method} {request.url.path} took {process_time:.2f}s")
    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    return response


@app.middleware("http")
async def cors_error_safety(request: Request, call_next):
    try:
        response = await call_next(request)
        # Add CORS headers to all responses
        origin = request.headers.get("origin", "")
        if origin in _cors_list:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        origin = request.headers.get("origin", "")
        headers = {}
        if origin in _cors_list:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Vary"] = "Origin"
        detail = f"{type(e).__name__}: {str(e) or 'unknown error'}"
        return JSONResponse(status_code=500, content={"detail": detail}, headers=headers)


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in _cors_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
    import traceback
    traceback.print_exc()
    detail = f"{type(exc).__name__}: {str(exc) or 'unknown error'}"
    return JSONResponse(status_code=500, content={"detail": detail}, headers=headers)


# ── Static files ───────────────────────────────────────────────────────────────

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


# ── Background Scheduler ───────────────────────────────────────────────────────

def _run_outreach_lifecycle():
    from app.schedulers.outreach_machine import process_outreach_lifecycle_states
    if not _acquire_scheduler_lock("outreach_lifecycle", 3500):
        return
    process_outreach_lifecycle_states(SessionLocal, Lead, Proposal, log_audit)


def _run_subscription_deductions():
    if not _acquire_scheduler_lock("subscription_deductions", 82800):
        return
    db = SessionLocal()
    try:
        deducted = _deduct_due_subscriptions(db)
        if deducted:
            print(f"[SCHEDULER] subscriptions deducted={len(deducted)}", flush=True)
    finally:
        db.close()


def _start_background_scheduler():
    if os.getenv("ENABLE_BACKGROUND_SCHEDULER", "true").lower() != "true":
        return None
    from apscheduler.schedulers.background import BackgroundScheduler
    sched = BackgroundScheduler(timezone="Asia/Jakarta", daemon=True)
    sched.add_job(_run_async_job, "interval", minutes=1, args=[process_pending_blasts], id="pending-blasts", max_instances=1, coalesce=True)
    sched.add_job(_run_async_job, "interval", hours=1, args=[scheduled_followup_processor], id="followups", max_instances=1, coalesce=True)
    sched.add_job(_run_outreach_lifecycle, "interval", hours=1, id="outreach-lifecycle", max_instances=1, coalesce=True)
    sched.add_job(_run_subscription_deductions, "cron", hour=0, minute=5, id="subscription-deductions", max_instances=1, coalesce=True)
    sched.start()
    return sched


background_scheduler = _start_background_scheduler()


# ── Include Routers ────────────────────────────────────────────────────────────

from routers import (  # noqa: E402
    auth, leads, proposals, finance, clients, workspace,
    documents, content, campaign, analytics, office, other,
)
from routers import settings as settings_router  # noqa: E402

app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(proposals.router)
app.include_router(finance.router)
app.include_router(clients.router)
app.include_router(workspace.router)
app.include_router(documents.router)
app.include_router(content.router)
app.include_router(settings_router.router)
app.include_router(campaign.router)
app.include_router(analytics.router)
app.include_router(office.router)
app.include_router(other.router)

# ── Backward compatibility: re-export functions used by tests/scripts ─────────
from routers.auth import login, logout, list_users, get_me, update_me  # noqa: E402
from routers.leads import delete_lead  # noqa: E402
from routers.other import send_wa_manual  # noqa: E402
from routers.finance import get_finance_reports  # noqa: E402
from routers.documents import (  # noqa: E402
    delete_archive_folder, update_archive_doc,
    preview_document, _render_document_pdf,
    _prepare_document_vars, _build_default_vars,
    _build_brand_context,
)
