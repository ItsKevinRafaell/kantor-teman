import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from models import get_db, log_audit, DATABASE_URL, SessionLocal, User, Lead, Contact, Proposal, ProposalAnalytics, Product, FollowUpSequence, ScrapeHistory, LeadAnalysis
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, GOOGLE_API_KEY,
    JWT_SECRET,
    FRONTEND_URL, _check_simple_rate_limit, search_semaphore,
    normalize_phone_storage, _normalize_phone, make_wa_url,
    calculate_lead_score, calculate_lead_score_full,
    generate_batch_name, generate_report_for_lead,
    get_fonnte_token, _send_fonnte_sync, _get_setting, ADMIN_WA,
    log_ai_cost, log_outreach_cost,
    get_ai_config, build_analysis_prompt, _call_ai_sync, call_ai_provider, parse_ai_response,
    _analysis_jobs, _blast_jobs,
)
from app.services.lead_service import (
    get_leads_with_ghost_viewer_flag,
    update_lead_status as _svc_update_lead_status,
    recalculate_lead_score as _svc_recalculate_lead_score,
    recalculate_all_lead_scores,
)
from app.services.scoring_service import (
    get_scoring_settings,
    save_scoring_settings,
    set_manual_score_adjustment,
    recalculate_lead_score_with_context,
)
from app.services.notification_service import create_notification
from app.constants import CLIENT_STATUS_VALUES
from app.core.cache import cached, clear_cache_prefix
try:
    from app.core.config import PLACES_NEW_SEARCH_URL
except Exception:
    PLACES_NEW_SEARCH_URL = os.environ.get("PLACES_NEW_SEARCH_URL", "https://places.googleapis.com/v1/places:searchText")

router = APIRouter()

PRODUCT_INTEREST_LABELS = {
    "web_development": "Web Development",
    "seo_google_maps": "SEO & Google Maps",
    "kelola_sosial_media": "Kelola Sosial Media",
    "maintenance_website": "Maintenance Website",
    "desain_logo": "Desain Logo",
}


def _places_error_message(resp: httpx.Response) -> str:
    try:
        payload = resp.json()
    except Exception:
        return f"HTTP {resp.status_code}: {resp.text[:200]}"
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("status")
        if message:
            return str(message)
    return f"HTTP {resp.status_code}"


def _is_autolead_source(source: str) -> bool:
    value = (source or "").lower()
    return "leadbot" in value or "autolead" in value


def _sync_autolead_context(db: Session, lead: Lead, body: ExternalLeadIn, duplicate: bool) -> None:
    if body.lead_stage or body.lead_score is not None or body.ai_reason or body.conversation_id:
        lines = [
            "AutoLead AI handoff",
            f"Stage: {body.lead_stage or '-'}",
            f"Score: {body.lead_score if body.lead_score is not None else '-'}",
            f"Reason: {body.ai_reason or '-'}",
            f"Conversation: {body.conversation_id or '-'}",
        ]
        if body.message:
            lines.append(f"Message: {body.message[:500]}")
        db.add(LeadAnalysis(
            lead_id=lead.id,
            analysis="\n".join(lines),
            pain_points=json.dumps([body.ai_reason] if body.ai_reason else []),
            suggested_product=body.product_interest or "",
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        ))
        db.flush()

    lead.score_adjustment = 0
    lead.score_adjustment_reason = None
    db.flush()
    local_score, _ = recalculate_lead_score_with_context(db, lead)
    if body.lead_score is not None:
        adjustment = max(-100, min(100, int(body.lead_score) - local_score))
        lead.score_adjustment = adjustment
        lead.score_adjustment_reason = f"AutoLead score sync: {body.lead_score}"
        recalculate_lead_score_with_context(db, lead)
        lead.lead_score = int(body.lead_score)

    score_text = f"score {body.lead_score}" if body.lead_score is not None else f"score {lead.lead_score or 0}"
    stage_text = f", stage {body.lead_stage}" if body.lead_stage else ""
    title = "Update prospek dari AutoLead" if duplicate else "Prospek baru dari AutoLead"
    create_notification(
        db,
        title=title,
        message=f"{lead.business_name} masuk dari AutoLead ({score_text}{stage_text}).",
        notif_type="warning" if (body.lead_score or lead.lead_score or 0) >= 70 else "info",
        target_type="lead",
        target_id=lead.id,
        action_url="/leads",
    )


def _fallback_analysis_payload(lead: Lead, error: Exception | None = None) -> dict:
    category = lead.product_interest or "bisnis"
    business = lead.business_name or "bisnis ini"
    location = lead.address or "area sekitar"
    pain_points = [
        f"{business} perlu terlihat lebih kuat saat calon pelanggan mencari {category} di Google.",
        f"Informasi online untuk {business} perlu dibuat lebih meyakinkan agar calon pelanggan tidak langsung pindah ke kompetitor.",
        f"Area {location} punya peluang lead lokal yang bisa ditangkap lewat optimasi Google Maps dan follow-up WhatsApp yang rapi.",
    ]
    suggested_product = category if category else "SEO & Google Maps"
    approach_message = (
        f"Halo {business}, kami baru cek peluang digital bisnis Anda. Ada beberapa bagian yang bisa dirapikan "
        f"supaya calon pelanggan di {location} lebih mudah menemukan dan percaya dengan bisnis Anda. "
        "Boleh kami kirimkan ringkasan audit singkatnya?"
    )
    analysis = {
        "pain_points": pain_points,
        "suggested_product": suggested_product,
        "approach_message": approach_message,
    }
    note = ""
    if error:
        note = f"\n\nCatatan sistem: AI upstream sedang lambat/terputus, analisis ini dibuat dari fallback rule internal. Detail: {str(error)[:160]}"
    return {
        "text": json.dumps(analysis, ensure_ascii=False) + note,
        "parsed": analysis,
        "fallback": True,
    }


def _save_lead_analysis(db: Session, lead: Lead, text: str, parsed: dict) -> LeadAnalysis:
    analysis = LeadAnalysis(
        lead_id=lead.id,
        analysis=text,
        pain_points=json.dumps(parsed.get("pain_points", [])),
        suggested_product=parsed.get("suggested_product", ""),
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _persist_lead_analysis_with_retry(session_factory, lead: Lead, text: str, parsed: dict, max_attempts: int = 2) -> LeadAnalysis:
    last_error = None
    for attempt in range(1, max_attempts + 1):
        db = session_factory()
        try:
            return _save_lead_analysis(db, lead, text, parsed)
        except OperationalError as exc:
            db.rollback()
            last_error = exc
            if attempt >= max_attempts:
                raise
            time.sleep(0.5 * attempt)
        finally:
            try:
                db.close()
            except Exception:
                pass
    raise last_error or RuntimeError("Gagal menyimpan analisis lead")


@router.post("/api/leads/external", status_code=201)
def create_external_lead(request: Request, body: ExternalLeadIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    import threading, httpx as _httpx

    api_key = request.headers.get("X-API-Key", "")
    stored_key = _get_setting("external_lead_api_key", "")
    if not stored_key or not hmac.compare_digest(api_key, stored_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    _check_simple_rate_limit(f"external_lead:{api_key[:16]}", 30, 60)

    phone = normalize_phone_storage(body.phone_number)
    if not phone:
        raise HTTPException(status_code=422, detail="Nomor WhatsApp tidak valid")

    existing = db.query(Lead).filter(Lead.phone_number == phone).first()

    if existing:
        note_text = f"[{body.source[:64]}] {(body.message or '')[:200]} (duplikat {datetime.now(timezone.utc).strftime('%Y-%m-%d')})"
        existing.batch_name = (existing.batch_name or "")[-200:] + f" | {note_text}"
        if existing.status == "Scraped":
            existing.status = "Replied"
        if _is_autolead_source(body.source):
            _sync_autolead_context(db, existing, body, duplicate=True)
        db.commit()
        clear_cache_prefix("cache:/api/leads")
        return {"lead_id": existing.id, "success": True, "duplicate": True}

    try:
        lead = Lead(
            business_name=body.business_name,
            phone_number=phone,
            status="Replied",
            product_interest=body.product_interest or "",
            batch_name="Web Form",
            lead_score=70,
        )
        db.add(lead)
        db.flush()
        if _is_autolead_source(body.source):
            _sync_autolead_context(db, lead, body, duplicate=False)
        else:
            lead.lead_score, _ = calculate_lead_score(lead)
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        existing = db.query(Lead).filter(Lead.phone_number == phone).first()
        if existing:
            return {"lead_id": existing.id, "success": True, "duplicate": True}
        raise HTTPException(status_code=500, detail="Gagal membuat lead")

    fonnte_token = get_fonnte_token(db)
    admin_wa = _get_setting("admin_wa", ADMIN_WA)
    msg = (
        f"🔥 *Lead baru dari website!*\n\n"
        f"Nama: *{body.business_name}*\n"
        f"WA: {phone}\n"
        f"Layanan: {PRODUCT_INTEREST_LABELS.get(body.product_interest or '', body.product_interest or '-')}\n"
        f"Email: {body.email or '-'}\n"
        f"Sumber: {body.source}\n"
    )
    if body.message:
        msg += f"\nPesan: {body.message}"

    threading.Thread(
        target=_send_fonnte_sync,
        args=(admin_wa, msg, fonnte_token, _httpx),
        daemon=True,
    ).start()

    if not _is_autolead_source(body.source):
        db_url = os.getenv("DATABASE_URL", "sqlite:///./leads.db")
        background_tasks.add_task(
            _send_wa_auto_reply_sync,
            lead.id, phone, body.business_name,
            body.product_interest or "", db_url, JWT_SECRET,
        )

    clear_cache_prefix("cache:/api/leads")
    return {"lead_id": lead.id, "success": True, "duplicate": False}



@router.get("/api/search", response_model=list[Business])
async def search_businesses(
    q: str = Query(...),
    max_results: int = Query(20, ge=1, le=60),
    product_interest: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    async with search_semaphore:
        api_key = _get_setting("google_api_key", GOOGLE_API_KEY or "")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

        batch = generate_batch_name(category or "", location or "")
        results: list[Business] = []
        page_token: Optional[str] = None

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.internationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.location,nextPageToken",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            while len(results) < max_results:
                body: dict = {"textQuery": q, "pageSize": min(20, max_results - len(results)), "languageCode": "id"}
                if page_token:
                    body["pageToken"] = page_token

                try:
                    resp = await client.post(PLACES_NEW_SEARCH_URL, json=body, headers=headers)
                except httpx.TimeoutException:
                    raise HTTPException(status_code=504, detail="Google Places timeout. Coba ulang dengan target hasil lebih kecil.")
                except httpx.HTTPError as exc:
                    raise HTTPException(status_code=502, detail=f"Gagal menghubungi Google Places: {str(exc)[:180]}")
                if resp.status_code != 200:
                    detail = _places_error_message(resp)
                    raise HTTPException(status_code=502, detail=f"Google Places error: {detail}")

                data = resp.json()
                for place in data.get("places", []):
                    if len(results) >= max_results:
                        break
                    raw_phone = place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber")
                    phone_digits = normalize_phone_storage(raw_phone) if raw_phone else None
                    wa_url = make_wa_url(phone_digits) if phone_digits else None
                    address = place.get("formattedAddress", "")
                    name = place.get("displayName", {}).get("text", "")
                    website = place.get("websiteUri")
                    google_rating = place.get("rating")
                    user_ratings_total = place.get("userRatingCount")
                    location_data = place.get("location", {})
                    latitude = location_data.get("latitude") if location_data else None
                    longitude = location_data.get("longitude") if location_data else None
                    if phone_digits and not db.query(Lead).filter(Lead.phone_number == phone_digits).first():
                        new_lead = Lead(business_name=name, phone_number=phone_digits, address=address,
                                    original_url=wa_url, product_interest=product_interest, batch_name=batch,
                                    website_url=website, google_rating=google_rating,
                                    review_count=user_ratings_total, latitude=latitude, longitude=longitude)
                        db.add(new_lead)
                        db.flush()
                        new_lead.lead_score, _ = calculate_lead_score(new_lead)
                        db.commit()
                    results.append(Business(name=name, address=address, phone=raw_phone, whatsapp_url=wa_url,
                                            google_rating=google_rating, review_count=user_ratings_total, website_url=website))

                page_token = data.get("nextPageToken")
                if not page_token:
                    break
                await asyncio.sleep(1.5)

        # Record scrape history
        db.add(ScrapeHistory(
            category=category or q,
            location=location or "",
            product_interest=product_interest,
            results_count=len(results),
            scraped_at=datetime.now(timezone.utc).isoformat(),
            batch_name=batch,
        ))
        db.commit()

        return results



@router.get("/api/leads/map")
@cached(ttl_seconds=30, key_func=lambda r: f"cache:/api/leads/map?{r.url.query}")
def get_leads_map(
    request: Request,
    status: Optional[str] = Query(None),
    batch_name: Optional[str] = Query(None),
    product_interest: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Lead).filter(Lead.latitude.isnot(None), Lead.longitude.isnot(None), Lead.is_archived == False)
    if status:
        query = query.filter(Lead.status == status)
    if batch_name:
        query = query.filter(Lead.batch_name == batch_name)
    if product_interest:
        query = query.filter(Lead.product_interest == product_interest)
    leads = query.all()
    return [{
        "id": lead.id,
        "business_name": lead.business_name,
        "phone_number": lead.phone_number,
        "address": lead.address,
        "status": lead.status,
        "product_interest": lead.product_interest,
        "batch_name": lead.batch_name,
        "website_url": lead.website_url,
        "google_rating": lead.google_rating,
        "review_count": lead.review_count,
        "latitude": lead.latitude,
        "longitude": lead.longitude,
        "lead_score": lead.lead_score or 0,
    } for lead in leads]


class LeadCreate(BaseModel):
    business_name: str = Field(..., max_length=200)
    phone_number: str = Field(..., max_length=30)
    address: Optional[str] = Field(None, max_length=500)
    product_interest: Optional[str] = Field(None, max_length=100)
    batch_name: Optional[str] = Field(None, max_length=100)


class LeadEdit(BaseModel):
    business_name: Optional[str] = Field(None, max_length=200)
    phone_number: Optional[str] = Field(None, max_length=30)
    address: Optional[str] = Field(None, max_length=500)
    product_interest: Optional[str] = Field(None, max_length=100)
    batch_name: Optional[str] = Field(None, max_length=100)



@router.get("/api/leads", response_model=list[LeadOut])
@cached(ttl_seconds=30, key_func=lambda r: f"cache:/api/leads?{r.url.query}")
def list_leads(
    request: Request,
    status: Optional[str] = Query(None),
    batch_name: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    archived_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_leads_with_ghost_viewer_flag(
        db, status=status, batch_name=batch_name,
        include_archived=include_archived, archived_only=archived_only,
    )



@router.post("/api/leads", response_model=LeadOut, status_code=201)
def create_lead_manual(body: LeadCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    existing = db.query(Lead).filter(Lead.phone_number == body.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Nomor {body.phone_number} sudah ada di database ({existing.business_name}).")
    lead = Lead(
        business_name=body.business_name,
        phone_number=body.phone_number,
        address=body.address,
        product_interest=body.product_interest,
        batch_name=body.batch_name or "Manual",
        status="Scraped",
        rating=0,
        lead_score=0,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    log_audit(db, current_user.name, "CREATE", "leads", lead.id, {"source": "manual"})
    clear_cache_prefix("cache:/api/leads")
    return lead


class WaSendIn(BaseModel):
    lead_id: int
    message: str



@router.put("/api/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, body: LeadEdit, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    changes = {}
    if body.business_name is not None:
        changes["business_name"] = {"old": lead.business_name, "new": body.business_name}
        lead.business_name = body.business_name
    if body.phone_number is not None:
        changes["phone_number"] = {"old": lead.phone_number, "new": body.phone_number}
        lead.phone_number = body.phone_number
    if body.address is not None:
        changes["address"] = {"old": lead.address, "new": body.address}
        lead.address = body.address
    if body.product_interest is not None:
        changes["product_interest"] = {"old": lead.product_interest, "new": body.product_interest}
        lead.product_interest = body.product_interest
    if body.batch_name is not None:
        changes["batch_name"] = {"old": lead.batch_name, "new": body.batch_name}
        lead.batch_name = body.batch_name
    db.commit()
    db.refresh(lead)
    lead.lead_score, _ = calculate_lead_score(lead)
    db.commit()
    if changes:
        log_audit(db, current_user.name, "UPDATE", "leads", lead_id, changes)
    clear_cache_prefix("cache:/api/leads")
    return lead



@router.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    lead.is_archived = True
    lead.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    log_audit(db, current_user.name, "ARCHIVE", "leads", lead_id, {"business_name": lead.business_name})
    clear_cache_prefix("cache:/api/leads")
    return {"detail": "Lead berhasil diarsipkan"}



@router.get("/api/leads/batches")
def get_batches(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Lead.batch_name).where(Lead.batch_name.isnot(None)).distinct()).scalars().all()
    return [r for r in rows if r]



@router.post("/api/leads/recalculate-scores")
def recalculate_all_scores(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return recalculate_all_lead_scores(db)


@router.get("/api/leads/scoring-settings")
def get_lead_scoring_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"settings": get_scoring_settings(db)}


@router.put("/api/leads/scoring-settings")
def update_lead_scoring_settings(body: ScoringSettingsUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    settings = save_scoring_settings(db, body.settings, current_user.name)
    result = recalculate_all_lead_scores(db)
    return {"settings": settings, "recalculated": result}



@router.post("/api/leads/{lead_id}/recalculate")
def recalculate_lead_score(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    score, breakdown = _svc_recalculate_lead_score(db, lead_id)
    return {"lead_id": lead_id, "score": score, "breakdown": breakdown}


@router.patch("/api/leads/{lead_id}/score-adjustment")
def update_lead_score_adjustment(
    lead_id: int,
    body: ScoreAdjustmentUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        score, breakdown = set_manual_score_adjustment(db, lead_id, body.adjustment, body.reason, current_user.name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"lead_id": lead_id, "score": score, "breakdown": breakdown}



@router.get("/api/leads/top-scored")
def get_top_scored_leads(limit: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(
        Lead.is_archived == False,
        Lead.status.notin_(list(CLIENT_STATUS_VALUES) + ["Closed/Lost"]),
    ).order_by(Lead.lead_score.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "business_name": l.business_name,
            "phone_number": l.phone_number,
            "lead_score": l.lead_score,
            "status": l.status,
            "product_interest": l.product_interest,
            "address": l.address,
        }
        for l in leads
    ]



@router.patch("/api/leads/{lead_id}/status", response_model=LeadOut)
def update_lead_status(lead_id: int, body: StatusUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = _svc_update_lead_status(db, lead_id, body.status, current_user.name)
    return lead



@router.patch("/api/leads/{lead_id}/product", response_model=LeadOut)
def update_lead_product(lead_id: int, body: ProductUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    lead.product_interest = body.product_interest
    db.commit()
    db.refresh(lead)
    return lead



@router.patch("/api/leads/{lead_id}/sales", response_model=LeadOut)
def update_lead_sales(lead_id: int, body: LeadSalesUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key == "do_not_contact":
            setattr(lead, key, bool(value))
        else:
            setattr(lead, key, value or None)
    if lead.do_not_contact:
        db.query(FollowUpSequence).filter(
            FollowUpSequence.lead_id == lead.id,
            FollowUpSequence.status == "ACTIVE",
        ).update({"status": "STOPPED", "stopped_reason": "opt_out"}, synchronize_session=False)
    db.commit()
    db.refresh(lead)
    log_audit(db, current_user.name, "UPDATE", "leads", lead_id, {"fields": list(changes)})
    return lead



@router.patch("/api/leads/{lead_id}/rating", response_model=LeadOut)
def update_lead_rating(lead_id: int, body: RatingUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=400, detail="Rating harus antara 1-5")
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    lead.rating = body.rating
    db.commit()
    db.refresh(lead)
    return lead



@router.post("/api/leads/{lead_id}/convert", response_model=ContactOut)
def convert_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    existing = db.query(Contact).filter(Contact.phone_number == lead.phone_number).first()
    if existing:
        lead.status = "Closed/Client"
        if not existing.lead_id:
            existing.lead_id = lead.id  # Link if not set
        db.commit()
        return existing
    contact = Contact(
        business_name=lead.business_name,
        phone_number=lead.phone_number,
        purchased_product=lead.product_interest,
        lead_id=lead.id,  # Link Contact to Lead
    )
    db.add(contact)
    lead.status = "Closed/Client"
    db.commit()
    db.refresh(contact)
    return contact





@router.post("/api/leads/restore/{lead_id}", response_model=LeadOut)
def restore_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    lead.is_archived = False
    lead.deleted_at = None
    db.commit()
    db.refresh(lead)
    log_audit(db, current_user.name, "RESTORE", "leads", lead_id, {"business_name": lead.business_name})
    return lead



@router.delete("/api/leads/batch/{batch_name}", status_code=204)
def delete_batch(batch_name: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.batch_name == batch_name, Lead.is_archived == False).all()
    if not leads:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")
    for lead in leads:
        lead.is_archived = True
        lead.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    log_audit(db, current_user.name, "DELETE", "leads", batch_name, {"action": "batch_delete", "count": len(leads)})


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


@router.get("/api/contacts", response_model=list[ContactOut])
def get_contacts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Contact).all()



@router.post("/api/contacts", response_model=ContactOut, status_code=201)
def create_contact(body: ContactUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.business_name or not body.phone_number:
        raise HTTPException(status_code=400, detail="Nama bisnis dan nomor WA wajib diisi")

    # Normalize phone number
    normalized_phone = normalize_phone_storage(body.phone_number)
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="Nomor WA tidak valid")

    # Check uniqueness
    existing = db.query(Contact).filter(Contact.phone_number == normalized_phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nomor WA sudah terdaftar")

    # Auto-create Lead if not exists (for Project linkage)
    lead = db.query(Lead).filter(Lead.phone_number == normalized_phone).first()
    if not lead:
        lead = Lead(
            business_name=body.business_name,
            phone_number=normalized_phone,
            status="Closed/Client",
            product_interest=body.purchased_product,
        )
        db.add(lead)
        db.flush()  # Get lead.id before creating contact

    contact = Contact(
        business_name=body.business_name,
        phone_number=normalized_phone,
        owner_name=body.owner_name,
        purchased_product=body.purchased_product,
        notes=body.notes,
        lead_id=lead.id,  # Link Contact to Lead
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    log_audit(db, current_user.name, "CREATE", "contacts", contact.id, {"business_name": body.business_name})
    return contact



@router.patch("/api/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, body: ContactUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Kontak tidak ditemukan")

    # Persist business_name on Contact
    if body.business_name is not None:
        contact.business_name = body.business_name

    # Handle phone_number with normalization and uniqueness check
    if body.phone_number is not None:
        normalized = normalize_phone_storage(body.phone_number)
        if not normalized:
            raise HTTPException(status_code=400, detail="Nomor WA tidak valid")
        # Check uniqueness if phone changes
        if normalized != contact.phone_number:
            existing = db.query(Contact).filter(
                Contact.phone_number == normalized,
                Contact.id != contact_id,
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="Nomor WA sudah terdaftar")
        contact.phone_number = normalized

    if body.owner_name is not None:
        contact.owner_name = body.owner_name
    if body.purchased_product is not None:
        contact.purchased_product = body.purchased_product
    if body.notes is not None:
        contact.notes = body.notes

    # Sync to Lead if linked
    if contact.lead_id:
        lead = db.query(Lead).filter(Lead.id == contact.lead_id).first()
        if lead:
            if body.business_name is not None:
                lead.business_name = body.business_name
            if body.phone_number is not None:
                lead.phone_number = normalize_phone_storage(body.phone_number)
            if body.purchased_product is not None:
                lead.product_interest = body.purchased_product

    db.commit()
    db.refresh(contact)
    return contact



@router.delete("/api/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Kontak tidak ditemukan")
    db.delete(contact)
    db.commit()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@router.get("/api/leads/hot")
def get_hot_leads(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    threshold_24h = (now - timedelta(hours=24)).isoformat()

    records = db.query(ProposalAnalytics, Proposal, Lead).join(
        Proposal, ProposalAnalytics.proposal_id == Proposal.id
    ).join(
        Lead, Proposal.lead_id == Lead.id
    ).filter(
        ProposalAnalytics.opened_at >= threshold_24h
    ).order_by(ProposalAnalytics.opened_at.desc()).all()

    seen_leads = {}
    for analytics, proposal, lead in records:
        if lead.id in seen_leads:
            seen_leads[lead.id]["total_opens"] += 1
            continue

        last_ping = analytics.last_ping
        opened_at = analytics.opened_at

        if last_ping:
            try:
                ping_time = datetime.fromisoformat(last_ping.replace("Z", "+00:00"))
                minutes_ago = (now - ping_time).total_seconds() / 60
            except Exception:
                minutes_ago = 999
        else:
            minutes_ago = 999

        if minutes_ago <= 5:
            status = "online"
        elif minutes_ago <= 60:
            status = "recent"
        else:
            status = "today"

        seen_leads[lead.id] = {
            "lead_id": lead.id,
            "business_name": lead.business_name,
            "phone_number": lead.phone_number,
            "category": lead.product_interest,
            "status": status,
            "last_active": last_ping or opened_at,
            "total_opens": 1,
            "proposal_slug": proposal.slug,
        }

    results = sorted(seen_leads.values(), key=lambda x: {"online": 0, "recent": 1, "today": 2}[x["status"]])
    return results



@router.post("/api/leads/{lead_id}/generate-report")
def generate_report_endpoint(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    slug = generate_report_for_lead(lead, db)
    frontend_url = (_get_setting("frontend_url", os.environ.get("FRONTEND_URL", FRONTEND_URL)) or FRONTEND_URL).rstrip("/")
    return {"slug": slug, "report_url": f"{frontend_url}/r/{slug}"}



@router.post("/api/leads/{lead_id}/analyze")
async def analyze_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    config = get_ai_config(db, "analysis")
    if config.get("provider") == "none":
        raise HTTPException(status_code=400, detail="AI provider belum dikonfigurasi. Silakan setup AI provider di Settings.")

    products = db.query(Product).filter(Product.is_active == True).all()
    product_list = "\n".join([f"- {p.name}: {p.description or ''}" for p in products]) if products else "- SEO\n- Web Development\n- Social Media Management"

    prompt = build_analysis_prompt(lead, product_list)

    db.close()
    fallback_used = False
    try:
        text = await call_ai_provider(prompt, config)
        parsed = parse_ai_response(text)

        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4
        try:
            cost_db = SessionLocal()
            log_ai_cost(cost_db, None, config["provider"], input_tokens, output_tokens)
        except Exception as cost_error:
            print(f"[AI ANALYZE COST WARN] lead={lead_id} error={cost_error}", flush=True)
        finally:
            try:
                cost_db.close()
            except Exception:
                pass
    except Exception as e:
        payload = _fallback_analysis_payload(lead, e)
        text = payload["text"]
        parsed = payload["parsed"]
        fallback_used = True
        print(f"[AI ANALYZE FALLBACK] lead={lead_id} error={e}", flush=True)

    analysis = _persist_lead_analysis_with_retry(SessionLocal, lead, text, parsed)

    return {
        "id": analysis.id,
        "lead_id": lead_id,
        "analysis": text,
        "pain_points": parsed.get("pain_points", []),
        "suggested_product": parsed.get("suggested_product", ""),
        "approach_message": parsed.get("approach_message", ""),
        "fallback": fallback_used,
        "analyzed_at": analysis.analyzed_at,
    }



@router.get("/api/leads/{lead_id}/analysis")
def get_lead_analysis(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead_id).order_by(LeadAnalysis.id.desc()).all()
    results = []
    for a in analyses:
        results.append({
            "id": a.id,
            "lead_id": a.lead_id,
            "analysis": a.analysis,
            "pain_points": json.loads(a.pain_points) if a.pain_points else [],
            "suggested_product": a.suggested_product,
            "analyzed_at": a.analyzed_at,
        })
    return results



@router.post("/api/leads/analyze-batch")
async def analyze_batch(
    batch_name: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    config = get_ai_config(db, "analysis")
    leads = db.query(Lead).filter(Lead.batch_name == batch_name, Lead.is_archived == False).all()
    already_analyzed = {a.lead_id for a in db.query(LeadAnalysis.lead_id).all()}
    to_analyze = [l for l in leads if l.id not in already_analyzed]
    lead_ids_to_analyze = [l.id for l in to_analyze]
    if not to_analyze:
        return {"message": "Semua lead di batch ini sudah dianalisa.", "analyzed": 0, "total": 0, "status": "done"}

    config = get_ai_config(db, "analysis")
    if config.get("provider") == "none":
        raise HTTPException(status_code=400, detail="AI provider belum dikonfigurasi. Silakan setup AI provider di Settings.")

    # Store job status in memory
    job_id = batch_name
    _analysis_jobs[job_id] = {"status": "running", "total": len(lead_ids_to_analyze), "analyzed": 0, "failed": 0, "batch_name": batch_name}

    # Run in background thread (WSGI kills event loop after response)
    def run_analysis_sync():
        import httpx as _httpx
        import time as _time
        from sqlalchemy import create_engine as _ce
        from sqlalchemy.orm import sessionmaker as _sm
        from sqlalchemy.pool import NullPool
        _ca = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        _engine = _ce(DATABASE_URL, connect_args=_ca, poolclass=NullPool)
        _Session = _sm(bind=_engine)
        try:
            _db = _Session()
            _config = get_ai_config(_db, "analysis")
            if _config.get("provider") == "none":
                _db.close()
                _analysis_jobs[job_id]["status"] = "error"
                _analysis_jobs[job_id]["error"] = "AI provider belum dikonfigurasi"
                return
            _products = _db.query(Product).filter(Product.is_active == True).all()
            _product_list = "\n".join([f"- {p.name}: {p.description or ''}" for p in _products]) if _products else "- SEO\n- Web Development"
            _db.close()
            analyzed = 0
            for lead_id in lead_ids_to_analyze:
                _db = _Session()
                try:
                    lead = _db.query(Lead).filter(Lead.id == lead_id, Lead.is_archived == False).first()
                    if not lead:
                        _db.close()
                        continue
                    existing = _db.query(LeadAnalysis.id).filter(LeadAnalysis.lead_id == lead.id).first()
                    if existing:
                        _db.close()
                        continue
                    prompt = build_analysis_prompt(lead, _product_list)
                    _db.close()
                    try:
                        text = _call_ai_sync(prompt, _config, _httpx)
                        parsed = parse_ai_response(text)
                    except Exception as ai_error:
                        payload = _fallback_analysis_payload(lead, ai_error)
                        text = payload["text"]
                        parsed = payload["parsed"]
                        print(f"[AI ANALYZE FALLBACK] lead={lead.id} error={ai_error}", flush=True)
                    analysis = _persist_lead_analysis_with_retry(_Session, lead, text, parsed)
                    current_lead_id = lead.id
                    analyzed += 1
                    _analysis_jobs[job_id]["analyzed"] = analyzed
                    _save_job_state()
                    print(f"[AI ANALYZE PROGRESS] {analyzed}/{len(lead_ids_to_analyze)} lead_id={current_lead_id}", flush=True)
                    _time.sleep(1)
                except Exception as e:
                    import traceback
                    print(f"[AI ANALYZE ERROR] lead={lead_id} error={e}", flush=True)
                    traceback.print_exc()
                    _analysis_jobs[job_id]["error"] = str(e)
                    _analysis_jobs[job_id]["failed"] = _analysis_jobs[job_id].get("failed", 0) + 1
                    try:
                        _db.close()
                    except Exception:
                        pass
                    continue
            _analysis_jobs[job_id]["status"] = "done"
            _analysis_jobs[job_id]["analyzed"] = analyzed
            _save_job_state()
            print(f"[AI ANALYZE DONE] analyzed={analyzed}/{len(lead_ids_to_analyze)} failed={_analysis_jobs[job_id].get('failed', 0)}", flush=True)
        except Exception as e:
            import traceback
            print(f"[AI ANALYZE FATAL] error={e}", flush=True)
            traceback.print_exc()
            _analysis_jobs[job_id]["status"] = "error"
            _analysis_jobs[job_id]["error"] = str(e)
            _save_job_state()
        finally:
            _engine.dispose()

    import threading
    threading.Thread(target=run_analysis_sync, daemon=False).start()
    return {"message": f"Analisa dimulai untuk {len(lead_ids_to_analyze)} leads.", "analyzed": 0, "total": len(lead_ids_to_analyze), "status": "running", "job_id": job_id}


# In-memory job tracker with file persistence
import json as _json, os as _os
_JOB_STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "analysis_jobs.json")

def _load_jobs():
    global _analysis_jobs
    try:
        if _os.path.exists(_JOB_STATE_FILE):
            with open(_JOB_STATE_FILE) as f:
                _analysis_jobs.update(_json.load(f))
    except:
        pass
    return _analysis_jobs

def _save_job_state():
    try:
        with open(_JOB_STATE_FILE, "w") as f:
            _json.dump(_analysis_jobs, f)
    except:
        pass

_analysis_jobs: dict = {}
_blast_jobs: dict = {}
_load_jobs()



@router.get("/api/leads/analyze-status")
def get_analyze_status(
    batch_name: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _analysis_jobs.get(batch_name)
    # Always try loading from file for cross-worker visibility
    if _os.path.exists(_JOB_STATE_FILE):
        try:
            with open(_JOB_STATE_FILE) as f:
                all_jobs = _json.load(f)
            file_job = all_jobs.get(batch_name)
            if file_job:
                # File has newer data — prefer "done" status from file over stale in-memory
                if not job or (file_job.get("status") == "done" and job.get("status") != "done"):
                    _analysis_jobs[batch_name] = file_job
                    job = file_job
        except Exception:
            pass
    if not job:
        lead_ids = [
            row[0] for row in db.query(Lead.id)
            .filter(Lead.batch_name == batch_name, Lead.is_archived == False)
            .all()
        ]
        if not lead_ids:
            return {"status": "idle", "analyzed": 0, "total": 0}
        analyzed = db.query(LeadAnalysis.lead_id).filter(
            LeadAnalysis.lead_id.in_(lead_ids)
        ).distinct().count()
        status = "done" if analyzed >= len(lead_ids) else "running"
        return {"status": status, "analyzed": analyzed, "total": len(lead_ids), "batch_name": batch_name}
    return job


@router.get("/api/leads/analyze-cancel")
def cancel_analyze(
    batch_name: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    """Mark analysis job as cancelled so progress widget stops polling."""
    job = _analysis_jobs.get(batch_name)
    if job and job.get("status") == "running":
        job["status"] = "cancelled"
        _save_job_state()
    # Also clear from file so stale state doesn't persist
    try:
        if _os.path.exists(_JOB_STATE_FILE):
            with open(_JOB_STATE_FILE) as f:
                all_jobs = _json.load(f)
            all_jobs.pop(batch_name, None)
            with open(_JOB_STATE_FILE, "w") as f:
                _json.dump(all_jobs, f)
            _analysis_jobs.pop(batch_name, None)
    except Exception:
        pass
    return {"status": "cancelled", "batch_name": batch_name}
