"""Web preview endpoints.

- POST /api/web-preview/generate/{lead_id}  (admin) — generate/reuse preview
- GET  /api/web-preview/lead/{lead_id}      (auth)  — info preview utk UI lead
- GET  /wp/{slug}                            (public) — HTML + tracking buka
"""
import html as html_mod

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from models import get_db, log_audit, User, Lead
from app.core.dependencies import get_current_user, require_admin
from app.services import web_preview_service

router = APIRouter()


@router.post("/api/web-preview/generate/{lead_id}")
def generate_web_preview(
    lead_id: int,
    body: dict = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.is_archived == False).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")

    body = body or {}
    template_key = body.get("template_key") or None
    force_new = bool(body.get("force_new"))

    if template_key and template_key not in web_preview_service.REGISTRY:
        raise HTTPException(status_code=422, detail=f"Template '{template_key}' tidak terdaftar")

    result = web_preview_service.generate_preview_for_lead(
        lead, db, template_key=template_key, force_new=force_new
    )
    log_audit(db, current_user.name, "CREATE", "web_previews", result["slug"], {
        "lead_id": lead_id, "template_key": result["template_key"], "reused": result["reused"],
    })
    return {
        **result,
        "url": web_preview_service.preview_public_url(db, result["slug"]),
    }


@router.get("/api/web-preview/lead/{lead_id}")
def get_web_preview_for_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    info = web_preview_service.get_preview_info(db, lead_id)
    if not info:
        return {"exists": False}
    return {"exists": True, **info}


@router.get("/wp/{slug}")
def view_web_preview(slug: str, db: Session = Depends(get_db)):
    html = web_preview_service.record_open_and_get_html(db, slug)
    if html is None:
        raise HTTPException(status_code=404, detail="Preview tidak ditemukan")
    # Defensive: slug dari path ga pernah masuk HTML, tapi jaga tetap aman.
    _ = html_mod.escape(slug)
    return HTMLResponse(content=html, status_code=200)
