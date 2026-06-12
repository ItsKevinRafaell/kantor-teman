import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from models import get_db, log_audit, User, Lead, MessageTemplate, ClientDocument, BrandKit, BrandAsset, DocumentTemplate, GeneratedDocument, Document, DocumentFolder, DocumentSequence, PaymentMethod, SystemSettings, ClientCredential, ProviderConfig, DynamicTemplate, BoardCard, BoardCardAttachment, BoardCardActivity
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, UPLOADS_DIR,
    encrypt_password, decrypt_password,
    log_outreach_cost,
    build_analysis_prompt, call_ai_provider, parse_ai_response,
    _detect_project_type, _detect_service_type, _detect_contract_months,
    _check_simple_rate_limit, _call_ai_sync,
)
from app.core.whatsapp_provider import send_whatsapp_message_sync
from app.constants import LeadStatus
from app.services import board_service

router = APIRouter()


def _raise_board_http_error(exc: Exception) -> None:
    detail = str(exc)
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=403, detail=detail)
    if "tidak ditemukan" in detail.lower():
        raise HTTPException(status_code=404, detail=detail)
    if "terhubung ke workspace" in detail.lower():
        raise HTTPException(status_code=409, detail=detail)
    raise HTTPException(status_code=400, detail=detail)

@router.post("/api/wa/send")
def send_wa_manual(body: WaSendIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_simple_rate_limit(f"wa_send:{current_user.id}", 20, 60)
    print(f"[WA SEND] lead_id={body.lead_id}", flush=True)
    lead = db.query(Lead).filter(Lead.id == body.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    if lead.do_not_contact:
        raise HTTPException(status_code=409, detail="Lead memilih opt-out. Pengiriman WhatsApp diblokir.")
    import httpx as _httpx
    result = send_whatsapp_message_sync(db, lead.phone_number, body.message, _httpx, {
        "lead_id": lead.id,
        "request_id": f"manual:{lead.id}:{int(time.time())}",
        "business_name": lead.business_name,
    })
    print(f"[WA SEND] provider={result.provider} success={result.ok}", flush=True)
    if result.ok:
        if lead.status == "Scraped":
            lead.status = LeadStatus.WA_SENT
            db.commit()
        log_outreach_cost(db, None, 1)
        log_audit(db, current_user.name, "SEND_WA", "leads", lead.id, {"type": "manual"})
        return {"success": True, "message": f"Pesan terkirim via {result.provider.upper()}."}
    raise HTTPException(status_code=502, detail=f"Gagal mengirim pesan via {result.provider.upper()}: {result.error or 'provider error'}")



@router.get("/api/public/proposal-templates")
def get_proposal_templates(db: Session = Depends(get_db)):
    intro = db.query(DynamicTemplate).filter(
        DynamicTemplate.type.in_(["PROPOSAL_INTRO", "PROPOSAL_TEXT"]),
        DynamicTemplate.is_active == True,
    ).first()
    outro = db.query(DynamicTemplate).filter(
        DynamicTemplate.type == "PROPOSAL_OUTRO",
        DynamicTemplate.is_active == True,
    ).first()
    return {
        "intro": intro.content if intro else None,
        "outro": outro.content if outro else None,
    }


# ---------------------------------------------------------------------------
# Proposals
# ---------------------------------------------------------------------------

def _proposal_to_out(proposal, lead) -> ProposalOut:
    timeline = None
    if proposal.timeline_data:
        timeline = sorted(json.loads(proposal.timeline_data), key=lambda x: x["sequence"])
    roi = None
    if proposal.roi_data:
        roi = json.loads(proposal.roi_data) if isinstance(proposal.roi_data, str) else proposal.roi_data
    return ProposalOut(
        id=proposal.id,
        lead_id=proposal.lead_id,
        services_detail=[ServiceDetail(**s) for s in json.loads(proposal.services_detail)],
        total_price=proposal.total_price,
        additional_options=proposal.additional_options,
        status=proposal.status,
        created_at=proposal.created_at,
        business_name=lead.business_name if lead else None,
        phone_number=lead.phone_number if lead else None,
        slug=proposal.slug,
        timeline_data=timeline,
        roi_data=roi,
    )



@router.get("/p/{slug}")
def redirect_proposal_by_slug(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        return HTMLResponse(
            content="<html><body style='font-family:sans-serif;text-align:center;padding:80px'><h1>404</h1><p>Proposal tidak ditemukan.</p></body></html>",
            status_code=404,
        )
    log_audit(db, "visitor", "VIEW", "proposals", proposal.id, {"slug": slug, "via": "short_link"})
    frontend_url = os.environ.get("FRONTEND_URL", "https://kantorteman.my.id")
    return RedirectResponse(url=f"{frontend_url}/proposal/{proposal.id}", status_code=307)



@router.get("/api/og-image/{slug}")
def og_image_simple(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug, Proposal.status == "Report").first()
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first() if proposal else None
    business_name = lead.business_name if lead else "Bisnis Anda"
    category = lead.product_interest if lead else ""
    safe_name = html_mod.escape(business_name[:40])
    safe_category = html_mod.escape(category)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#09090b"/>
<rect width="1200" height="4" fill="#f59e0b"/>
<rect y="626" width="1200" height="4" fill="#10b981"/>
<text x="600" y="200" text-anchor="middle" font-family="Arial,sans-serif" font-size="24" fill="#a1a1aa" letter-spacing="2">LAPORAN HASIL AUDIT DIGITAL</text>
<text x="600" y="320" text-anchor="middle" font-family="Arial,sans-serif" font-size="52" font-weight="bold" fill="#fafafa">{safe_name}</text>
<text x="600" y="380" text-anchor="middle" font-family="Arial,sans-serif" font-size="22" fill="#71717a">{safe_category}</text>
<text x="600" y="520" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" fill="#52525b">Diterbitkan oleh Teman UMKM Kita Agensi</text>
</svg>"""
    return HTMLResponse(content=svg, status_code=200, media_type="image/svg+xml")



@router.get("/api/timeline-templates")
def get_timeline_templates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    templates = db.query(DynamicTemplate).filter(
        DynamicTemplate.type == "TIMELINE_TEMPLATE",
        DynamicTemplate.is_active == True,
    ).all()
    result = []
    for t in templates:
        items = json.loads(t.content) if t.content else []
        sorted_items = sorted(items, key=lambda x: x.get("sequence", 0))
        result.append({
            "id": t.id,
            "name": t.name,
            "category_id": t.category_id,
            "timeline_data": sorted_items,
        })
    return result



@router.put("/api/board-columns/{column_id}", response_model=BoardColumnOut)
def update_board_column(column_id: str, body: BoardColumnIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update column name, position or color"""
    try:
        return board_service.update_board_column(db, column_id, body.name, body.position, body.color)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.delete("/api/board-columns/{column_id}", status_code=204)
def delete_board_column(column_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Delete a column and all its cards"""
    try:
        board_service.delete_board_column(db, column_id)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.post("/api/board-columns/{column_id}/cards", response_model=BoardCardOut, status_code=201)
def create_board_card(column_id: str, body: BoardCardIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new card in column"""
    try:
        return board_service.create_board_card(
            db,
            column_id,
            body.title,
            body.description,
            body.assignee,
            body.due_date,
            body.labels,
            body.lead_id,
            body.color or "gray",
            current_user.name,
        )
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.get("/api/board-cards/{card_id}", response_model=BoardCardOut)
def get_board_card(card_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get card details"""
    try:
        return board_service.get_board_card(db, card_id)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.put("/api/board-cards/{card_id}", response_model=BoardCardOut)
def update_board_card(card_id: str, body: BoardCardUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update card"""
    updates = body.model_dump(exclude_unset=True)
    try:
        return board_service.update_board_card(db, card_id, updates, current_user.name)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.delete("/api/board-cards/{card_id}", status_code=204)
def delete_board_card(card_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Delete a card"""
    try:
        board_service.delete_board_card(db, card_id)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.post("/api/board-cards/{card_id}/move", response_model=BoardCardOut)
def move_board_card(card_id: str, body: MoveCardRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Move card to another column"""
    try:
        return board_service.move_board_card(
            db,
            card_id,
            body.column_id,
            body.position,
            current_user.name,
            current_user.role,
        )
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.post("/api/board-cards/{card_id}/comments", response_model=BoardCardCommentOut, status_code=201)
def create_card_comment(card_id: str, body: BoardCardCommentIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add comment to card"""
    try:
        return board_service.create_card_comment(db, card_id, current_user.name, body.content)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.post("/api/board-cards/{card_id}/checklist", response_model=BoardCardChecklistOut, status_code=201)
def create_card_checklist(card_id: str, body: BoardCardChecklistIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add checklist item to card"""
    try:
        return board_service.create_card_checklist(db, card_id, body.text, current_user.name)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)



@router.patch("/api/board-cards/{card_id}/checklist/{item_id}", response_model=BoardCardChecklistOut)
def update_card_checklist(card_id: str, item_id: str, is_done: bool = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle checklist item"""
    try:
        return board_service.toggle_checklist_item(db, card_id, item_id, is_done, current_user.name)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)


@router.post("/api/board-cards/{card_id}/attachments", response_model=BoardCardAttachmentOut, status_code=201)
async def upload_board_card_attachment(
    card_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    allowed_ext = {".jpg", ".jpeg", ".png", ".pdf", ".webp", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Format tidak diizinkan: {ext or '-'}")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File terlalu besar (max 10MB)")

    card_dir = os.path.join(UPLOADS_DIR, "board", card_id)
    os.makedirs(card_dir, exist_ok=True)
    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = os.path.join(card_dir, fname)
    with open(fpath, "wb") as fh:
        fh.write(contents)

    file_url = f"/uploads/board/{card_id}/{fname}"
    attachment = BoardCardAttachment(
        id=str(uuid.uuid4()),
        card_id=card_id,
        file_path=file_url,
        file_name=file.filename or fname,
        file_type=file.content_type,
        uploaded_by=current_user.name,
    )
    db.add(attachment)
    db.add(BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="attachment",
        description=f"File ditambahkan: {attachment.file_name}",
        actor=current_user.name,
    ))
    card.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(attachment)
    return attachment


# ---------------------------------------------------------------------------
# Client Notes
# ---------------------------------------------------------------------------


@router.get("/api/client-notes", response_model=list[ClientNoteOut])
def get_client_notes(
    lead_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(ClientNote).filter(ClientNote.lead_id == lead_id).order_by(ClientNote.id.desc()).all()



@router.post("/api/client-notes", response_model=ClientNoteOut, status_code=201)
def create_client_note(body: ClientNoteIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.category not in ("BISNIS", "TEKNIS", "PENTING"):
        raise HTTPException(status_code=400, detail="Category harus 'BISNIS', 'TEKNIS', atau 'PENTING'")
    note = ClientNote(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=current_user.name,
        category=body.category,
        content=body.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note



@router.delete("/api/client-notes/{note_id}", status_code=204)
def delete_client_note(note_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.query(ClientNote).filter(ClientNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note tidak ditemukan")
    db.delete(note)
    db.commit()



@router.get("/api/credentials", response_model=list[CredentialOut])
def get_credentials(
    lead_id: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(ClientCredential)
    if lead_id == "internal":
        query = query.filter(ClientCredential.lead_id.is_(None))
    elif lead_id:
        query = query.filter(ClientCredential.lead_id == int(lead_id))
    creds = query.order_by(ClientCredential.created_at.desc()).all()
    results = []
    for c in creds:
        raw_fields = json.loads(c.fields) if c.fields else []
        decrypted_fields = []
        for f in raw_fields:
            val = f["value"]
            if f.get("is_secret"):
                try:
                    val = decrypt_password(val)
                except Exception:
                    val = "***decryption_error***"
            decrypted_fields.append(CredentialFieldOut(key=f["key"], value=val, is_secret=f.get("is_secret", False)))
        results.append(CredentialOut(
            id=c.id, lead_id=c.lead_id, category=c.category, title=c.title,
            fields=decrypted_fields, created_at=c.created_at,
        ))
    return results



@router.post("/api/credentials", response_model=CredentialOut, status_code=201)
def create_credential(body: CredentialIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    stored_fields = []
    for f in body.fields:
        val = encrypt_password(f.value) if f.is_secret else f.value
        stored_fields.append({"key": f.key, "value": val, "is_secret": f.is_secret})
    cred = ClientCredential(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        category=body.category,
        title=body.title,
        fields=json.dumps(stored_fields),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    log_audit(db, current_user.name, "CREATE", "client_credentials", cred.id, {"title": body.title, "category": body.category})
    out_fields = [CredentialFieldOut(key=f.key, value=f.value, is_secret=f.is_secret) for f in body.fields]
    return CredentialOut(
        id=cred.id, lead_id=cred.lead_id, category=cred.category, title=cred.title,
        fields=out_fields, created_at=cred.created_at,
    )



@router.put("/api/credentials/{cred_id}", response_model=CredentialOut)
def update_credential(cred_id: str, body: CredentialUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    cred = db.query(ClientCredential).filter(ClientCredential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential tidak ditemukan")
    if body.category is not None:
        cred.category = body.category
    if body.title is not None:
        cred.title = body.title
    if body.fields is not None:
        stored_fields = []
        for f in body.fields:
            val = encrypt_password(f.value) if f.is_secret else f.value
            stored_fields.append({"key": f.key, "value": val, "is_secret": f.is_secret})
        cred.fields = json.dumps(stored_fields)
    db.commit()
    db.refresh(cred)
    raw_fields = json.loads(cred.fields) if cred.fields else []
    out_fields = []
    for f in raw_fields:
        val = f["value"]
        if f.get("is_secret"):
            try:
                val = decrypt_password(val)
            except Exception:
                val = "***decryption_error***"
        out_fields.append(CredentialFieldOut(key=f["key"], value=val, is_secret=f.get("is_secret", False)))
    log_audit(db, current_user.name, "UPDATE", "client_credentials", cred_id, {"title": cred.title})
    return CredentialOut(
        id=cred.id, lead_id=cred.lead_id, category=cred.category, title=cred.title,
        fields=out_fields, created_at=cred.created_at,
    )



@router.delete("/api/credentials/{cred_id}", status_code=204)
def delete_credential(cred_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    cred = db.query(ClientCredential).filter(ClientCredential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential tidak ditemukan")
    log_audit(db, current_user.name, "DELETE", "client_credentials", cred_id, {"title": cred.title})
    db.delete(cred)
    db.commit()


# ---------------------------------------------------------------------------
# Credential Categories Management
# ---------------------------------------------------------------------------


@router.get("/api/credential-categories")
def get_credential_categories(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="credential_categories").first()
    if row and row.value:
        return json.loads(row.value)
    return ["WordPress", "Google Account", "Sosmed", "Server", "Email", "Hosting", "Domain", "Analytics"]



@router.put("/api/credential-categories")
def update_credential_categories(categories: list[str], current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="credential_categories").first()
    if row:
        row.value = json.dumps(categories)
    else:
        db.add(SystemSettings(key="credential_categories", value=json.dumps(categories)))
    db.commit()
    return categories


# ---------------------------------------------------------------------------
# Client Documents (Cloud Links)
# ---------------------------------------------------------------------------


@router.post("/api/brand-assets", status_code=201)
def create_brand_asset(body: BrandAssetIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    kit = _get_active_kit(db)
    asset = BrandAsset(
        id=str(uuid.uuid4()),
        kit_id=kit.id,
        asset_type=body.asset_type,
        name=body.name,
        value=body.value,
        file_url=body.file_url,
        position=body.position or 0,
        asset_metadata=body.asset_metadata,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"id": asset.id, "asset_type": asset.asset_type, "name": asset.name, "value": asset.value, "file_url": asset.file_url, "position": asset.position, "asset_metadata": asset.asset_metadata}



@router.put("/api/brand-assets/{asset_id}")
def update_brand_asset(asset_id: str, body: BrandAssetIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    asset = db.query(BrandAsset).filter(BrandAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset tidak ditemukan")
    asset.asset_type = body.asset_type
    asset.name = body.name
    asset.value = body.value
    asset.file_url = body.file_url
    asset.position = body.position or 0
    asset.asset_metadata = body.asset_metadata
    db.commit()
    return {"id": asset.id, "asset_type": asset.asset_type, "name": asset.name, "value": asset.value, "file_url": asset.file_url, "position": asset.position, "asset_metadata": asset.asset_metadata}



@router.delete("/api/brand-assets/{asset_id}", status_code=204)
def delete_brand_asset(asset_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    asset = db.query(BrandAsset).filter(BrandAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset tidak ditemukan")
    db.delete(asset)
    db.commit()



@router.post("/api/brand-assets/upload")
async def upload_brand_asset_file(
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    name: str = Form(...),
    asset_id: Optional[str] = Form(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".ico", ".svg"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Format tidak diizinkan: {ext}")

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File terlalu besar (max 2MB)")

    brand_dir = os.path.join(UPLOADS_DIR, "brand")
    os.makedirs(brand_dir, exist_ok=True)
    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = os.path.join(brand_dir, fname)
    with open(fpath, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/brand/{fname}"
    kit = _get_active_kit(db)

    if asset_id:
        asset = db.query(BrandAsset).filter(BrandAsset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset tidak ditemukan")
        asset.file_url = file_url
        asset.name = name
        asset.asset_type = asset_type
        db.commit()
        return {"id": asset.id, "file_url": file_url, "name": name, "asset_type": asset_type}

    asset = BrandAsset(
        id=str(uuid.uuid4()),
        kit_id=kit.id,
        asset_type=asset_type,
        name=name,
        file_url=file_url,
        position=0,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"id": asset.id, "file_url": file_url, "name": name, "asset_type": asset_type}


# ---------------------------------------------------------------------------
# Document Generator
# ---------------------------------------------------------------------------

from document_template_library import get_document_template_starters

DOCUMENTS_DIR = os.path.join(UPLOADS_DIR, "documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)


class DocumentTemplateIn(BaseModel):
    name: str
    type: str
    html_template: str
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = True


class DocumentGenerateIn(BaseModel):
    template_id: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    variables: dict = Field(default_factory=dict)


class DocumentEmailIn(BaseModel):
    to_email: str
    subject: Optional[str] = None
    body: Optional[str] = None


def _serialize_template(t: DocumentTemplate) -> dict:
    try:
        vars_list = json.loads(t.variables or "[]")
    except Exception:
        vars_list = []
    return {
        "id": t.id,
        "name": t.name,
        "type": t.type,
        "html_template": t.html_template,
        "variables": vars_list,
        "is_active": t.is_active,
        "created_at": t.created_at,
    }



@router.get("/api/document-template-starters")
def list_document_template_starters(current_user: User = Depends(get_current_user)):
    return get_document_template_starters()



@router.get("/api/pixel/{document_id}")
def track_pdf_open(document_id: str):
    import threading
    def _log():
        db = None
        try:
            db = SessionLocal()
            doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == document_id).first()
            now = datetime.now(timezone.utc).isoformat()
            if doc and doc.target_id and doc.target_id.isdigit():
                lead_id = int(doc.target_id)
                db.add(LeadActivityLog(id=str(uuid.uuid4()), lead_id=lead_id, activity_type="pdf_opened"))
                proposal = db.query(Proposal).filter(Proposal.lead_id == lead_id).first()
                if proposal:
                    db.add(ProposalAnalytics(id=str(uuid.uuid4()), proposal_id=proposal.id, opened_at=now, event="pdf_opened"))
            db.commit()
        except Exception:
            pass
        finally:
            if db:
                try: db.close()
                except Exception: pass
    threading.Thread(target=_log, daemon=True).start()
    return Response(
        content=TRACKING_PIXEL_PNG,
        media_type="image/png",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )


_DOC_TYPE_PREFIX = {
    "invoice": "INV",
    "receipt": "RCPT",
    "proposal_pdf": "PROP",
    "kontrak": "KTR",
    "surat_penawaran": "SP",
    "custom": "DOC",
}


def _slugify_name(name: str, max_len: int = 30) -> str:
    if not name:
        return "Klien"
    s = re.sub(r"[^A-Za-z0-9\s-]", "", name).strip()
    s = re.sub(r"\s+", "-", s)
    return s[:max_len] or "Klien"


def _resolve_target_name(db: Session, target_type: Optional[str], target_id: Optional[str]) -> str:
    if not target_id:
        return "Umum"
    if target_type == "lead" and target_id.isdigit():
        lead = db.query(Lead).filter(Lead.id == int(target_id)).first()
        if lead and lead.business_name:
            return lead.business_name
    if target_type == "contact" and target_id.isdigit():
        contact = db.query(Contact).filter(Contact.id == int(target_id)).first()
        if contact and contact.business_name:
            return contact.business_name
    if target_type == "project":
        project = db.query(Project).filter(Project.id == target_id).first()
        if project and project.lead_id:
            lead = db.query(Lead).filter(Lead.id == project.lead_id).first()
            if lead and lead.business_name:
                return lead.business_name
    return "Umum"


def _next_doc_sequence(db: Session, target_id: str, template_type: str) -> int:
    key_target = target_id or "GLOBAL"
    seq = db.query(DocumentSequence).filter(
        DocumentSequence.target_id == key_target,
        DocumentSequence.template_type == template_type,
    ).with_for_update().first()
    if not seq:
        seq = DocumentSequence(target_id=key_target, template_type=template_type, last_seq=0)
        db.add(seq)
    seq.last_seq = (seq.last_seq or 0) + 1
    db.flush()
    return seq.last_seq


def _peek_doc_sequence(db: Session, target_id: str, template_type: str) -> int:
    seq = db.query(DocumentSequence).filter(
        DocumentSequence.target_id == (target_id or "GLOBAL"),
        DocumentSequence.template_type == template_type,
    ).first()
    return (seq.last_seq if seq else 0) + 1


def _generate_document_filename(db: Session, template_type: str, target_type: Optional[str], target_id: Optional[str]) -> str:
    prefix = _DOC_TYPE_PREFIX.get(template_type, "DOC")
    name = _resolve_target_name(db, target_type, target_id)
    slug = _slugify_name(name)
    seq = _next_doc_sequence(db, target_id or "GLOBAL", template_type)
    yyyymm = datetime.now(timezone.utc).strftime("%Y%m")
    return f"{prefix}_{slug}_{seq:03d}_{yyyymm}"



@router.get("/api/provider-configs", response_model=list[ProviderConfigOut])
def get_provider_configs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ProviderConfig).all()



@router.put("/api/provider-configs/{provider_id}")
def update_provider_config(provider_id: str, body: dict, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    provider = db.query(ProviderConfig).filter_by(id=provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    if "remaining_quota" in body:
        provider.remaining_quota = body["remaining_quota"]
    if "price_per_unit_idr" in body:
        provider.price_per_unit_idr = body["price_per_unit_idr"]
    if "price_input_token_usd" in body:
        provider.price_input_token_usd = body["price_input_token_usd"]
    if "price_output_token_usd" in body:
        provider.price_output_token_usd = body["price_output_token_usd"]
    db.commit()
    return {"ok": True}
