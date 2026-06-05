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
from models import get_db, log_audit, User, Lead, MessageTemplate, ClientDocument, BrandKit, BrandAsset, DocumentTemplate, GeneratedDocument, Document, DocumentFolder, DocumentSequence, PaymentMethod
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, UPLOADS_DIR,
    encrypt_password, decrypt_password,
    get_fonnte_token, _send_fonnte_sync, log_outreach_cost,
    get_ai_config, build_analysis_prompt, call_ai_provider, parse_ai_response,
    _detect_project_type, _detect_service_type, _detect_contract_months,
    _check_simple_rate_limit,
)

router = APIRouter()

@router.post("/api/wa/send")
def send_wa_manual(body: WaSendIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_simple_rate_limit(f"wa_send:{current_user.id}", 20, 60)
    print(f"[WA SEND] lead_id={body.lead_id}", flush=True)
    lead = db.query(Lead).filter(Lead.id == body.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    if lead.do_not_contact:
        raise HTTPException(status_code=409, detail="Lead memilih opt-out. Pengiriman WhatsApp diblokir.")
    token = get_fonnte_token(db)
    print(f"[WA SEND] phone={lead.phone_number} token=***", flush=True)
    if not token:
        raise HTTPException(status_code=400, detail="Fonnte token belum dikonfigurasi.")
    import httpx as _httpx
    success = _send_fonnte_sync(lead.phone_number, body.message, token, _httpx)
    print(f"[WA SEND] success={success}", flush=True)
    if success:
        if lead.status == "Scraped":
            lead.status = "Contacted"
            db.commit()
        log_outreach_cost(db, None, 1)
        log_audit(db, current_user.name, "SEND_WA", "leads", lead.id, {"type": "manual"})
        return {"success": True, "message": "Pesan terkirim via Fonnte."}
    raise HTTPException(status_code=502, detail="Gagal mengirim pesan via Fonnte.")



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


# ---------------------------------------------------------------------------
# AI Lead Analysis (Multi-Provider: Gemini, Claude, OpenAI)
# ---------------------------------------------------------------------------

def get_ai_config(db: Session, capability: str = "analysis") -> dict:
    """Per-feature AIProxy first, fallback to 9router. Optional model override per capability via ai_models registry."""
    proxy = get_proxy_for_feature(db, capability)
    if proxy:
        cfg = {
            "provider": "openai",
            "openai_key": proxy.api_key,
            "base_url": proxy.base_url.rstrip("/"),
            "model": proxy.model,
            "gemini_key": "",
            "claude_key": "",
        }
    else:
        cfg = get_9router_config(db)
    default_model = get_default_model(db, capability)
    if default_model and default_model.model_id:
        cfg["model"] = default_model.model_id
    return cfg


def build_analysis_prompt(lead, product_list: str) -> str:
    return f"""Kamu adalah konsultan digital marketing untuk UMKM Indonesia. Analisa bisnis berikut dan berikan insight yang persuasif dan mudah dipahami pemilik usaha.

DATA BISNIS:
- Nama: {lead.business_name}
- Alamat: {lead.address or 'Tidak diketahui'}
- Rating Google: {lead.rating}/5
- Kategori: {lead.product_interest or 'Umum'}

PRODUK/LAYANAN YANG KAMI TAWARKAN:
{product_list}

INSTRUKSI:
Berikan output dalam format JSON berikut (Bahasa Indonesia, gaya bicara santai tapi profesional):
{{
  "pain_points": ["masalah 1 yang spesifik dan relatable untuk pemilik usaha", "masalah 2", "masalah 3"],
  "suggested_product": "nama produk kami yang paling cocok",
  "approach_message": "satu paragraf pendek pesan WA yang bisa langsung dikirim ke pemilik bisnis ini, persuasif tapi tidak memaksa, sebutkan masalah mereka dan solusi kita"
}}

PENTING: Pain points harus spesifik ke bisnis ini, bukan generik. Pesan pendekatan harus terasa personal."""


def _call_ai_sync(prompt: str, config: dict, _httpx) -> str:
    provider = config["provider"]
    with _httpx.Client(timeout=120) as client:
        if provider == "gemini":
            if not config["gemini_key"]:
                raise Exception("Gemini API Key belum dikonfigurasi.")
            resp = client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                headers={"x-goog-api-key": config["gemini_key"]},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            if resp.status_code != 200:
                raise Exception(f"Gemini API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        elif provider == "claude":
            if not config["claude_key"]:
                raise Exception("Claude API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "claude-haiku-4-5-20251001"
            url = f"{base_url.rstrip('/')}/chat/completions"
            print(f"[AI CALL SYNC] url={url} model={model}", flush=True)
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {config['claude_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            print(f"[AI RESPONSE SYNC] status={resp.status_code} length={len(resp.text)}", flush=True)
            if resp.status_code != 200:
                raise Exception(f"Claude API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]
        elif provider == "openai":
            if not config["openai_key"]:
                raise Exception("OpenAI API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "gpt-4o-mini"
            resp = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['openai_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                },
            )
            if resp.status_code != 200:
                raise Exception(f"OpenAI API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Provider '{provider}' tidak dikenali.")


async def call_ai_provider(prompt: str, config: dict) -> str:
    provider = config["provider"]
    async with httpx.AsyncClient(timeout=60) as client:
        if provider == "gemini":
            if not config["gemini_key"]:
                raise HTTPException(status_code=400, detail="Gemini API Key belum dikonfigurasi.")
            resp = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                headers={"x-goog-api-key": config["gemini_key"]},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Gemini API error: {resp.status_code}")
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

        elif provider == "claude":
            if not config["claude_key"]:
                raise HTTPException(status_code=400, detail="Claude API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "claude-haiku-4-5-20251001"
            url = f"{base_url.rstrip('/')}/chat/completions"
            print(f"[AI CALL] provider=claude url={url} model={model} key=***", flush=True)
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {config['claude_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            print(f"[AI RESPONSE] status={resp.status_code} length={len(resp.text)}", flush=True)
            if resp.status_code != 200:
                print(f"[AI CALL ERROR] status={resp.status_code} body_len={len(resp.text)}", flush=True)
                raise HTTPException(status_code=502, detail=f"Claude API error: {resp.status_code}")
            return resp.json()["choices"][0]["message"]["content"]

        elif provider == "openai":
            if not config["openai_key"]:
                raise HTTPException(status_code=400, detail="OpenAI API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "gpt-4o-mini"
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['openai_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"OpenAI API error: {resp.status_code}")
            return resp.json()["choices"][0]["message"]["content"]

        else:
            raise HTTPException(status_code=400, detail=f"Provider '{provider}' tidak dikenali.")


def parse_ai_response(text: str) -> dict:
    import re as _re
    json_match = _re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass
    return {"pain_points": [text], "suggested_product": "", "approach_message": ""}



@router.put("/api/board-columns/{column_id}", response_model=BoardColumnOut)
def update_board_column(column_id: str, body: BoardColumnIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update column name, position or color"""
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column tidak ditemukan")
    if body.name:
        col.name = body.name
    if body.position is not None:
        col.position = body.position
    if body.color:
        col.color = body.color
    db.commit()
    db.refresh(col)
    return BoardColumnOut(id=col.id, board_id=col.board_id, name=col.name, position=col.position, color=col.color, cards=[])



@router.delete("/api/board-columns/{column_id}", status_code=204)
def delete_board_column(column_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Delete a column and all its cards"""
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column tidak ditemukan")
    card_ids = [c.id for c in db.query(BoardCard.id).filter(BoardCard.column_id == column_id).all()]
    if card_ids:
        db.query(BoardCardActivity).filter(BoardCardActivity.card_id.in_(card_ids)).delete(synchronize_session=False)
        db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id.in_(card_ids)).delete(synchronize_session=False)
        db.query(BoardCardComment).filter(BoardCardComment.card_id.in_(card_ids)).delete(synchronize_session=False)
    db.query(BoardCard).filter(BoardCard.column_id == column_id).delete()
    db.delete(col)
    db.commit()



@router.post("/api/board-columns/{column_id}/cards", response_model=BoardCardOut, status_code=201)
def create_board_card(column_id: str, body: BoardCardIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new card in column"""
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column tidak ditemukan")
    max_pos = db.query(BoardCard).filter(BoardCard.column_id == column_id).count()
    card = BoardCard(
        id=str(uuid.uuid4()),
        column_id=column_id,
        title=body.title,
        description=body.description,
        assignee=body.assignee or current_user.name,
        due_date=body.due_date,
        labels=json.dumps(body.labels) if body.labels else None,
        position=max_pos,
        lead_id=body.lead_id,
        color=body.color or "yellow",
    )
    db.add(card)

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="created",
        description=f"Card created: {body.title}",
        actor=current_user.name,
    )
    db.add(activity)
    db.commit()
    db.refresh(card)

    return card_to_out(card)



@router.get("/api/board-cards/{card_id}", response_model=BoardCardOut)
def get_board_card(card_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get card details"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")
    return card_to_out(card)



@router.put("/api/board-cards/{card_id}", response_model=BoardCardOut)
def update_board_card(card_id: str, body: BoardCardUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update card"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    # Block title edit if card is linked to workspace row (1-way sync)
    workspace_linked = db.query(WorkspaceRow).filter(WorkspaceRow.board_card_id == card_id).first()
    if body.title is not None and workspace_linked:
        pass  # ignore title change — managed by workspace
    elif body.title is not None:
        card.title = body.title
    if body.description is not None:
        card.description = body.description
    if body.assignee is not None:
        card.assignee = body.assignee
    if body.due_date is not None:
        card.due_date = body.due_date
    if body.labels is not None:
        card.labels = json.dumps(body.labels)
    if body.column_id is not None:
        card.column_id = body.column_id
    if body.position is not None:
        card.position = body.position
    if body.lead_id is not None:
        card.lead_id = body.lead_id
    if body.color is not None:
        card.color = body.color
    if body.is_archived is not None:
        card.is_archived = body.is_archived
        # Add activity for archive/unarchive
        action = "archived" if body.is_archived else "unarchived"
        activity = BoardCardActivity(
            id=str(uuid.uuid4()),
            card_id=card.id,
            action=action,
            description=f"Card {action}",
            actor=current_user.name,
        )
        db.add(activity)

    card.updated_at = datetime.now(timezone.utc).isoformat()

    # Add update activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="updated",
        description="Card updated",
        actor=current_user.name,
    )
    db.add(activity)

    db.commit()
    db.refresh(card)
    return card_to_out(card)



@router.delete("/api/board-cards/{card_id}", status_code=204)
def delete_board_card(card_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Delete a card"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")
    if db.query(WorkspaceRow).filter(WorkspaceRow.board_card_id == card_id).first():
        raise HTTPException(status_code=409, detail="Card terhubung ke workspace. Hapus task dari workspace agar sinkronisasi tetap konsisten.")
    db.query(BoardCardActivity).filter(BoardCardActivity.card_id == card_id).delete()
    db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id == card_id).delete()
    db.query(BoardCardComment).filter(BoardCardComment.card_id == card_id).delete()
    db.delete(card)
    db.commit()



@router.post("/api/board-cards/{card_id}/move", response_model=BoardCardOut)
def move_board_card(card_id: str, body: MoveCardRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Move card to another column"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    # Admin-only rule: moves to Done/Revisi columns require admin role
    target_column = db.query(BoardColumn).filter(BoardColumn.id == body.column_id).first()
    if target_column:
        target_name = (target_column.name or "").strip().lower()
        if target_name in {"done", "revisi", "selesai"} and (current_user.role or "").lower() != "admin":
            raise HTTPException(status_code=403, detail=f"Hanya admin yang bisa pindahin card ke '{target_column.name}'.")

    old_column = card.column_id
    card.column_id = body.column_id
    if body.position is not None:
        card.position = body.position
    else:
        max_pos = db.query(BoardCard).filter(BoardCard.column_id == body.column_id).count()
        card.position = max_pos

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="moved",
        description=f"Card moved to another column",
        actor=current_user.name,
    )
    db.add(activity)

    db.commit()
    db.refresh(card)
    return card_to_out(card)



@router.post("/api/board-cards/{card_id}/comments", response_model=BoardCardCommentOut, status_code=201)
def create_card_comment(card_id: str, body: BoardCardCommentIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add comment to card"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    comment = BoardCardComment(
        id=str(uuid.uuid4()),
        card_id=card_id,
        author=current_user.name,
        content=body.content,
    )
    db.add(comment)

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="commented",
        description=f"Comment added: {body.content[:50]}...",
        actor=current_user.name,
    )
    db.add(activity)
    db.commit()
    db.refresh(comment)
    return comment



@router.post("/api/board-cards/{card_id}/checklist", response_model=BoardCardChecklistOut, status_code=201)
def create_card_checklist(card_id: str, body: BoardCardChecklistIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add checklist item to card"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    max_pos = db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id == card_id).count()
    item = BoardCardChecklist(
        id=str(uuid.uuid4()),
        card_id=card_id,
        text=body.text,
        position=max_pos,
    )
    db.add(item)
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="checklist",
        description=f'Checklist "{body.text}" ditambahkan',
        actor=current_user.name,
    )
    db.add(activity)
    db.commit()
    db.refresh(item)
    return item



@router.patch("/api/board-cards/{card_id}/checklist/{item_id}", response_model=BoardCardChecklistOut)
def update_card_checklist(card_id: str, item_id: str, is_done: bool = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle checklist item"""
    item = db.query(BoardCardChecklist).filter(BoardCardChecklist.id == item_id, BoardCardChecklist.card_id == card_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item tidak ditemukan")
    item.is_done = is_done
    status_text = "selesai" if is_done else "belum selesai"
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="checklist",
        description=f'Checklist "{item.text}" ditandai {status_text}',
        actor=current_user.name,
    )
    db.add(activity)
    db.commit()
    db.refresh(item)
    return item


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



