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
from models import get_db, log_audit, AIModel, User, Lead, Product, Category, DynamicTemplate, MessageTemplate, BoardCardComment, BoardCardChecklist, BoardCardActivity, BoardCard, BoardColumn, Board, Project, ContentGeneration, ContentSession, ContentSchedule, Document, DocumentFolder, DocumentTemplate, GeneratedDocument, ReportSnapshot, BrandKit, ReengagementAlert, FollowUpSequence, ClientNote, ClientCredential, ClientDocument, LeadActivityLog, LeadAnalysis, Proposal, ProposalAnalytics, BlastMessage, BlastCampaign, AdsCampaign, ScrapeHistory, Contact, Subscription, Transaction, Wallet, ServiceItem, SystemSettings, AuditLog, WhatsAppNumber
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, verify_password,
    seed_data, get_fonnte_token, _send_fonnte_sync, _normalize_phone,
    _ai_model_to_out, _mask_secret, SENSITIVE_SETTING_KEYS, ADMIN_WA,
    _get_google_calendar_service, _get_setting, get_ai_config, UPLOADS_DIR,
    GOOGLE_CALENDAR_ID,
)
from app.core.config import DATABASE_URL, IS_PRODUCTION
from app.services.ai_service import fetch_9router_models_async
from app.services.sales_workflow_service import get_default_dp_percent, set_default_dp_percent
from app.constants import CLIENT_STATUS_VALUES

router = APIRouter()


def _require_dev():
    """Block destructive admin endpoints in production."""
    if IS_PRODUCTION:
        raise HTTPException(
            status_code=403,
            detail="Aksi ini dinonaktifkan di production. Hubungi admin server untuk akses dev/staging.",
        )

@router.get("/api/settings/production-mode")
def get_production_mode(current_user: User = Depends(require_admin)):
    """Return whether this instance is running in production mode."""
    return {"is_production": IS_PRODUCTION}


@router.get("/api/settings/billing-defaults")
def get_billing_defaults(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {"default_dp_percent": get_default_dp_percent(db)}


@router.put("/api/settings/billing-defaults")
def update_billing_defaults(body: dict = Body(...), current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    percent = body.get("default_dp_percent", 50)
    updated = set_default_dp_percent(db, percent)
    log_audit(db, current_user.name, "UPDATE", "system_settings", "default_dp_percent", {"value": updated})
    return {"default_dp_percent": updated}


@router.get("/api/settings")
def get_settings(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    keys = ["fonnte_token", "whatsapp_provider", "whatsapp_blast_delay_seconds", "ai_api_key", "ai_provider", "ai_base_url", "ai_model", "google_api_key", "google_calendar_id", "google_service_account_json", "admin_wa", "admin_name", "followup_enabled", "followup_hour", "cms_url", "cms_api_token", "external_lead_api_key", "smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from"]
    result = {}
    for k in keys:
        row = db.query(SystemSettings).filter_by(key=k).first()
        raw = row.value if row else ""
        result[k] = _mask_secret(raw) if k in SENSITIVE_SETTING_KEYS else raw
    result["ai_provider"] = "9router"
    result["whatsapp_provider"] = "fonnte"
    if not result.get("whatsapp_blast_delay_seconds"):
        result["whatsapp_blast_delay_seconds"] = "5"
    return result



@router.put("/api/settings")
def update_settings(body: SettingsUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    settings_map = {
        "fonnte_token": body.fonnte_token,
        "whatsapp_provider": "fonnte",
        "whatsapp_blast_delay_seconds": body.whatsapp_blast_delay_seconds,
        "ai_api_key": body.ai_api_key,
        "ai_provider": "9router",
        "ai_base_url": body.ai_base_url,
        "ai_model": body.ai_model,
        "google_api_key": body.google_api_key,
        "google_calendar_id": body.google_calendar_id,
        "google_service_account_json": body.google_service_account_json,
        "admin_wa": body.admin_wa,
        "admin_name": body.admin_name,
        "followup_enabled": body.followup_enabled,
        "followup_hour": body.followup_hour,
        "cms_url": body.cms_url,
        "cms_api_token": body.cms_api_token,
        "external_lead_api_key": body.external_lead_api_key,
        "smtp_host": body.smtp_host,
        "smtp_port": body.smtp_port,
        "smtp_user": body.smtp_user,
        "smtp_password": body.smtp_password,
        "smtp_from": body.smtp_from,
    }
    for key, value in settings_map.items():
        if value is not None:
            if key in SENSITIVE_SETTING_KEYS and isinstance(value, str) and value.startswith("****"):
                continue
            row = db.query(SystemSettings).filter_by(key=key).first()
            if row:
                row.value = value
            else:
                db.add(SystemSettings(key=key, value=value))
    db.commit()
    return {"ok": True}



@router.post("/api/settings/external-lead-key/regenerate")
def regenerate_external_lead_key(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    new_key = str(uuid.uuid4())
    row = db.query(SystemSettings).filter_by(key="external_lead_api_key").first()
    if row:
        row.value = new_key
    else:
        db.add(SystemSettings(key="external_lead_api_key", value=new_key))
    db.commit()
    return {"key": new_key}



class ExternalLeadIn(BaseModel):
    business_name: str
    phone_number: str
    email: Optional[str] = None
    message: Optional[str] = None
    product_interest: Optional[str] = None
    source: str = "website_temanumkmkita"

    @field_validator("source")
    @classmethod
    def cap_source(cls, v: str) -> str:
        return v[:64]

    @field_validator("message")
    @classmethod
    def cap_message(cls, v: Optional[str]) -> Optional[str]:
        return v[:500] if v else v


PRODUCT_INTEREST_LABELS = {
    "web_development": "Web Development",
    "seo_google_maps": "SEO & Google Maps",
    "kelola_sosial_media": "Kelola Sosial Media",
    "maintenance_website": "Maintenance Website",
    "desain_logo": "Desain Logo",
}


def _send_wa_auto_reply_sync(lead_id: int, phone: str, name: str, product_interest: str, db_url: str, jwt_secret: str):
    import httpx as _httpx
    db = SessionLocal()
    try:
        if not phone:
            return
        row = db.query(SystemSettings).filter_by(key="fonnte_token").first()
        token = (row.value or "") if row else ""
        if not token:
            print(f"[WA_AUTO_REPLY] fonnte_token missing, skip", flush=True)
            return
        label = PRODUCT_INTEREST_LABELS.get(product_interest, product_interest or "layanan kami")
        msg = (
            f"Halo {name}! 👋 Terima kasih sudah menghubungi kami. "
            f"Kami telah menerima permintaan Anda untuk layanan *{label}*. "
            f"Tim kami akan segera menghubungi Anda dalam waktu dekat. "
            f"Salam, Tim Teman UMKM Kita 🙏"
        )
        _send_fonnte_sync(phone, msg, token, _httpx)
        db.add(LeadActivityLog(
            id=str(uuid.uuid4()),
            lead_id=lead_id,
            activity_type="wa_auto_reply",
        ))
        db.commit()
    except Exception as e:
        print(f"[WA_AUTO_REPLY] error: {e}", flush=True)
    finally:
        db.close()



@router.post("/api/admin/seed")
def run_seed_endpoint(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    _require_dev()
    """Run seeder via HTTP — use once after first deploy."""
    from seed import categories, products_data, templates_data
    from document_template_library import get_document_template_starters
    import uuid as _uuid

    db.query(Product).delete()
    db.query(Category).delete()
    db.query(DynamicTemplate).filter(DynamicTemplate.type.in_(["WA_BLAST", "FOLLOW_UP"])).delete()
    db.commit()

    cat_objects = {}
    for key, cat in categories.items():
        c = Category(id=str(_uuid.uuid4()), name=cat["name"], description=cat["description"], is_active=True)
        db.add(c)
        cat_objects[key] = c
    db.commit()

    for name, desc, price, features, cat_key, is_retainer in products_data:
        db.add(Product(
            id=str(_uuid.uuid4()), name=name, description=desc, base_price=price,
            features=json.dumps(features), category_id=cat_objects[cat_key].id,
            is_active=True, is_retainer=is_retainer,
        ))
    db.commit()

    for name, ttype, cat_key, content in templates_data:
        db.add(DynamicTemplate(
            id=str(_uuid.uuid4()), name=name, type=ttype, content=content,
            is_active=True, category_id=cat_objects[cat_key].id,
        ))
    db.commit()

    # Seed DocumentTemplates
    starters = get_document_template_starters()
    existing_template_types = {t.type for t in db.query(DocumentTemplate).all()}
    for doc_type, data in starters.items():
        if doc_type not in existing_template_types:
            db.add(DocumentTemplate(
                id=str(_uuid.uuid4()),
                name=data["name"],
                type=doc_type,
                html_template=data["html_template"],
                variables=json.dumps(data["variables"]),
                is_active=True,
            ))
    db.commit()

    # Seed default BrandKit
    existing_kits = db.query(BrandKit).filter(BrandKit.is_active == True).count()
    if existing_kits == 0:
        db.add(BrandKit(
            id=str(_uuid.uuid4()),
            kit_name="Kantor Teman",
            brand_name="Kantor Teman",
            tagline="Partner Digital Bisnis Anda",
            phone="", email="", address="", logo="",
            is_active=True,
        ))
        db.commit()

    seed_data(db)
    return {"ok": True, "message": "Seed berhasil: categories, products, templates, document templates, brand kit"}


# ============================================================================
# DATA ADMIN — Backup, Reset (soft/nuclear), Seed
# ============================================================================

class DataAdminBody(BaseModel):
    password: str


def _verify_admin_password(user: User, password: str):
    if not password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Password salah")



@router.post("/api/admin/data/reset-soft")
def admin_data_reset_soft(
    body: DataAdminBody,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Soft reset: hapus data dev/test, pertahankan clients (Closed/Client), users, settings, products."""
    _require_dev()
    _verify_admin_password(current_user, body.password)
    try:
        db.query(BoardCardComment).delete()
        db.query(BoardCardChecklist).delete()
        db.query(BoardCardActivity).delete()
        db.query(BoardCard).delete()
        db.query(BoardColumn).delete()
        db.query(Board).delete()
        db.query(ContentGeneration).delete()
        db.query(ContentSession).delete()
        db.query(ContentSchedule).delete()
        try: db.query(ReportSnapshot).delete()
        except Exception: pass
        try: db.query(GeneratedDocument).delete()
        except Exception: pass
        db.query(Document).delete()
        db.query(DocumentFolder).delete()
        try: db.query(ProposalAnalytics).delete()
        except Exception: pass
        db.query(ReengagementAlert).delete()
        db.query(FollowUpSequence).delete()
        db.query(ClientNote).delete()
        db.query(ClientCredential).delete()
        db.query(ClientDocument).delete()
        db.query(LeadActivityLog).delete()
        db.query(LeadAnalysis).delete()
        db.query(Proposal).delete()
        try: db.query(BlastMessage).delete()
        except Exception: pass
        db.query(BlastCampaign).delete()
        db.query(AdsCampaign).delete()
        db.query(ScrapeHistory).delete()
        db.query(Lead).filter(Lead.status.notin_(CLIENT_STATUS_VALUES)).delete(synchronize_session=False)
        # Contact records are preserved — only dev/test leads are removed
        db.query(AuditLog).delete()
        db.query(MessageTemplate).delete()
        db.query(ServiceItem).delete()
        db.commit()
        return {"ok": True, "message": "Soft reset selesai. Data klien dan konfigurasi dipertahankan."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Reset gagal: {e}")



@router.post("/api/admin/data/reset-nuclear")
def admin_data_reset_nuclear(
    body: DataAdminBody,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Nuclear reset: hapus SEMUA data kecuali users, system_settings, provider_configs, ai_models. Auto-seed basic."""
    _require_dev()
    _verify_admin_password(current_user, body.password)
    try:
        db.query(BoardCardComment).delete()
        db.query(BoardCardChecklist).delete()
        db.query(BoardCardActivity).delete()
        db.query(BoardCard).delete()
        db.query(BoardColumn).delete()
        db.query(Board).delete()
        try: db.query(Project).delete()
        except Exception: pass
        db.query(ContentGeneration).delete()
        db.query(ContentSession).delete()
        db.query(ContentSchedule).delete()
        try: db.query(ReportSnapshot).delete()
        except Exception: pass
        try: db.query(GeneratedDocument).delete()
        except Exception: pass
        db.query(Document).delete()
        db.query(DocumentFolder).delete()
        try: db.query(ProposalAnalytics).delete()
        except Exception: pass
        db.query(ReengagementAlert).delete()
        db.query(FollowUpSequence).delete()
        db.query(ClientNote).delete()
        db.query(ClientCredential).delete()
        db.query(ClientDocument).delete()
        db.query(LeadActivityLog).delete()
        db.query(LeadAnalysis).delete()
        db.query(Proposal).delete()
        try: db.query(BlastMessage).delete()
        except Exception: pass
        db.query(BlastCampaign).delete()
        db.query(AdsCampaign).delete()
        db.query(ScrapeHistory).delete()
        db.query(Lead).delete()
        db.query(Contact).delete()
        db.query(Subscription).delete()
        db.query(Transaction).delete()
        db.query(Wallet).delete()
        db.query(Product).delete()
        db.query(Category).delete()
        db.query(DynamicTemplate).delete()
        db.query(MessageTemplate).delete()
        db.query(ServiceItem).delete()
        db.query(AuditLog).delete()
        db.commit()

        seed_data(db)
        db.commit()
        return {"ok": True, "message": "Nuclear reset selesai. Basic seed dijalankan otomatis."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Nuclear reset gagal: {e}")



@router.post("/api/admin/data/seed-demo")
def admin_data_seed_demo(
    body: DataAdminBody,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Re-seed demo data: categories, products, templates, wallets, sample clients."""
    _require_dev()
    _verify_admin_password(current_user, body.password)
    try:
        from seed import categories, products_data, templates_data, wallets_data, clients_data
        from document_template_library import get_document_template_starters
        import uuid as _uuid

        db.query(Product).delete()
        db.query(Category).delete()
        db.query(DynamicTemplate).filter(DynamicTemplate.type.in_(["WA_BLAST", "FOLLOW_UP"])).delete()
        db.commit()

        cat_objects = {}
        for key, cat in categories.items():
            c = Category(id=str(_uuid.uuid4()), name=cat["name"], description=cat["description"], is_active=True)
            db.add(c)
            cat_objects[key] = c
        db.commit()

        for name, desc, price, features, cat_key, is_retainer in products_data:
            db.add(Product(
                id=str(_uuid.uuid4()), name=name, description=desc, base_price=price,
                features=json.dumps(features), category_id=cat_objects[cat_key].id,
                is_active=True, is_retainer=is_retainer,
            ))
        db.commit()

        for name, ttype, cat_key, content in templates_data:
            db.add(DynamicTemplate(
                id=str(_uuid.uuid4()), name=name, type=ttype, content=content,
                is_active=True, category_id=cat_objects[cat_key].id,
            ))
        db.commit()

        existing_wallets = db.query(Wallet).count()
        if existing_wallets == 0:
            for w in wallets_data:
                db.add(Wallet(name=w["name"], balance=w["balance"], icon=w["icon"], color=w["color"]))
            db.commit()

        for biz, phone, owner, product in clients_data:
            exists = db.query(Lead).filter(Lead.business_name == biz).first()
            if not exists:
                db.add(Lead(
                    business_name=biz, phone_number=phone, owner_name=owner,
                    product_interest=product, status="Closed/Client",
                ))
        db.commit()

        seed_data(db)
        return {"ok": True, "message": "Demo seed berhasil: categories, products, templates, wallets, sample clients."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Seed gagal: {e}")



@router.get("/api/admin/data/backup")
def admin_data_backup(
    current_user: User = Depends(require_admin),
):
    """Backup full DB + uploads/ folder as zip. mysqldump for mysql, file copy for sqlite."""
    import subprocess
    import zipfile
    import tempfile
    import shutil
    from urllib.parse import urlparse, unquote

    db_url = DATABASE_URL
    is_mysql = "mysql" in db_url
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_zip.close()

    try:
        with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
            if is_mysql:
                parsed = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
                user = unquote(parsed.username or "")
                pw = unquote(parsed.password or "")
                host = parsed.hostname or "localhost"
                port = parsed.port or 3306
                dbname = (parsed.path or "/").lstrip("/")
                cmd = [
                    "mysqldump",
                    f"-h{host}", f"-P{port}", f"-u{user}", f"-p{pw}",
                    "--single-transaction", "--routines", "--triggers",
                    "--default-character-set=utf8mb4",
                    dbname,
                ]
                proc = subprocess.run(cmd, capture_output=True, timeout=300)
                if proc.returncode != 0:
                    raise HTTPException(status_code=500, detail=f"mysqldump gagal: {proc.stderr.decode(errors='ignore')[:500]}")
                zf.writestr(f"{dbname}.sql", proc.stdout)
            else:
                sqlite_path = unquote(db_url.replace("sqlite:///", ""))
                if sqlite_path and not os.path.isabs(sqlite_path):
                    sqlite_path = os.path.abspath(os.path.join(backend_dir, sqlite_path))
                if os.path.exists(sqlite_path):
                    zf.write(sqlite_path, arcname=os.path.basename(sqlite_path))

            uploads_dir = UPLOADS_DIR
            if os.path.isdir(uploads_dir):
                for root, _, files in os.walk(uploads_dir):
                    for f in files:
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, os.path.dirname(uploads_dir))
                        zf.write(full, arcname=rel)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"kantorteman-backup-{ts}.zip"
        default_backup_dir = os.path.abspath(os.path.join(backend_dir, "..", "..", "kantorteman-backups"))
        backup_dir = os.path.abspath(os.getenv("BACKUP_DIR", default_backup_dir))
        os.makedirs(backup_dir, exist_ok=True)
        stored_path = os.path.join(backup_dir, filename)
        shutil.copy2(tmp_zip.name, stored_path)

        def _iterfile():
            try:
                with open(stored_path, "rb") as f:
                    while chunk := f.read(65536):
                        yield chunk
            finally:
                try:
                    os.unlink(tmp_zip.name)
                except Exception:
                    pass

        return StreamingResponse(
            _iterfile(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        try: os.unlink(tmp_zip.name)
        except Exception: pass
        raise
    except Exception as e:
        try: os.unlink(tmp_zip.name)
        except Exception: pass
        raise HTTPException(status_code=500, detail=f"Backup gagal: {e}")



@router.post("/api/settings/test-api")
async def test_api_connection(
    provider: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test apakah API key yang disimpan bisa terhubung dengan benar."""
    config = get_ai_config(db)

    if provider == "fonnte":
        token = get_fonnte_token(db)
        if not token:
            return {"success": False, "message": "Token Fonnte belum diisi."}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.fonnte.com/validate",
                    headers={"Authorization": token},
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Fonnte terhubung."}
                return {"success": False, "message": f"Fonnte error: {resp.status_code} - {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"Gagal koneksi ke Fonnte: {str(e)}"}

    elif provider in ("9router", "ai", "router"):
        try:
            result = await fetch_9router_models_async(config)
            return {"success": True, "message": f"9router terhubung. {result.get('count', 0)} model/combo tersedia."}
        except Exception as e:
            return {"success": False, "message": f"Gagal koneksi ke 9router: {str(e)[:200]}"}

    return {"success": False, "message": f"Provider '{provider}' tidak dikenal."}



@router.post("/api/settings/test-calendar")
def test_calendar_connection(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Test Google Calendar connection."""
    try:
        service = _get_google_calendar_service()
        if not service:
            return {"success": False, "message": "Google Calendar service tidak bisa diinisialisasi. Cek google_service_account_json dan google_calendar_id di Settings."}
        calendar_id = _get_setting("google_calendar_id", GOOGLE_CALENDAR_ID)
        if not calendar_id:
            return {"success": False, "message": "google_calendar_id belum diisi di Settings."}
        probe = {
            "summary": "KantorTeman calendar test",
            "start": {"date": datetime.now(timezone.utc).date().isoformat()},
            "end": {"date": (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()},
        }
        created = service.events().insert(calendarId=calendar_id, body=probe).execute()
        event_id = created.get("id")
        if event_id:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return {"success": True, "message": f"Terhubung dan bisa tulis ke kalender: {calendar_id}"}
    except Exception as e:
        return {"success": False, "message": f"Gagal: {str(e)[:200]}"}


# ---------------------------------------------------------------------------
# AI Models CRUD (centralized model registry)
# ---------------------------------------------------------------------------

class AIModelIn(BaseModel):
    name: str
    model_id: str
    description: Optional[str] = None
    capabilities: List[str] = ["chat"]
    is_active: bool = True


class AIModelOut(BaseModel):
    id: str
    name: str
    model_id: str
    description: Optional[str]
    capabilities: List[str]
    is_active: bool
    is_default_chat: bool
    is_default_image: bool
    is_default_article: bool
    is_default_analysis: bool


def _ai_model_to_out(m: AIModel) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "model_id": m.model_id,
        "description": m.description,
        "capabilities": json.loads(m.capabilities or '["chat"]'),
        "is_active": bool(m.is_active),
        "is_default_chat": bool(m.is_default_chat),
        "is_default_image": bool(m.is_default_image),
        "is_default_article": bool(m.is_default_article),
        "is_default_analysis": bool(m.is_default_analysis),
    }



@router.get("/api/settings/services", response_model=list[ServiceItemOut])
def get_service_items(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    items = db.query(ServiceItem).all()
    results = []
    for item in items:
        results.append(ServiceItemOut(
            id=item.id,
            name=item.name,
            default_price=item.default_price,
            default_features=json.loads(item.default_features),
        ))
    return results



@router.post("/api/settings/services", response_model=ServiceItemOut, status_code=201)
def create_service_item(body: ServiceItemIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):

    item = ServiceItem(
        id=str(uuid.uuid4()),
        name=body.name,
        default_price=body.default_price,
        default_features=json.dumps(body.default_features),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ServiceItemOut(
        id=item.id,
        name=item.name,
        default_price=item.default_price,
        default_features=json.loads(item.default_features),
    )



@router.put("/api/settings/services/{item_id}", response_model=ServiceItemOut)
def update_service_item(item_id: str, body: ServiceItemIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):

    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Service item tidak ditemukan")
    item.name = body.name
    item.default_price = body.default_price
    item.default_features = json.dumps(body.default_features)
    db.commit()
    db.refresh(item)
    return ServiceItemOut(
        id=item.id,
        name=item.name,
        default_price=item.default_price,
        default_features=json.loads(item.default_features),
    )



@router.delete("/api/settings/services/{item_id}", status_code=204)
def delete_service_item(item_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Service item tidak ditemukan")
    db.delete(item)
    db.commit()


# ---------------------------------------------------------------------------
# Proposal Tracking (Public)
# ---------------------------------------------------------------------------


@router.get("/api/categories", response_model=list[CategoryOut])
def get_categories(
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Category)
    if active_only:
        query = query.filter(Category.is_active == True)
    return query.all()



@router.post("/api/categories", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Kategori dengan nama ini sudah ada")
    cat = Category(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        is_active=body.is_active,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    log_audit(db, current_user.name, "CREATE", "categories", cat.id, {"name": body.name})
    return cat



@router.put("/api/categories/{cat_id}", response_model=CategoryOut)
def update_category(cat_id: str, body: CategoryIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    dup = db.query(Category).filter(Category.name == body.name, Category.id != cat_id).first()
    if dup:
        raise HTTPException(status_code=400, detail="Kategori dengan nama ini sudah ada")
    cat.name = body.name
    cat.description = body.description
    cat.is_active = body.is_active
    db.commit()
    db.refresh(cat)
    log_audit(db, current_user.name, "UPDATE", "categories", cat_id, {"name": body.name})
    return cat



@router.delete("/api/categories/{cat_id}", status_code=204)
def delete_category(cat_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    db.delete(cat)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "categories", cat_id, {"name": cat.name})


# ---------------------------------------------------------------------------
# Master Data - Products
# ---------------------------------------------------------------------------

def _product_to_out(product, db) -> ProductOut:
    cat_name = None
    if product.category_id:
        cat = db.query(Category).filter(Category.id == product.category_id).first()
        cat_name = cat.name if cat else None
    return ProductOut(
        id=product.id, name=product.name, description=product.description,
        base_price=product.base_price, features=json.loads(product.features or "[]"),
        category_id=product.category_id, category_name=cat_name, is_active=product.is_active,
        is_retainer=product.is_retainer or False,
    )



@router.get("/api/products", response_model=list[ProductOut])
def get_products(
    category_id: Optional[str] = Query(None),
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    products = query.all()
    return [_product_to_out(p, db) for p in products]



@router.post("/api/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = Product(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        base_price=body.base_price,
        features=json.dumps(body.features),
        category_id=body.category_id,
        is_active=body.is_active,
        is_retainer=body.is_retainer,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    log_audit(db, current_user.name, "CREATE", "products", product.id, {"name": body.name})
    return _product_to_out(product, db)



@router.put("/api/products/{product_id}", response_model=ProductOut)
def update_product(product_id: str, body: ProductIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    product.name = body.name
    product.description = body.description
    product.base_price = body.base_price
    product.features = json.dumps(body.features)
    product.category_id = body.category_id
    product.is_active = body.is_active
    product.is_retainer = body.is_retainer
    db.commit()
    db.refresh(product)
    log_audit(db, current_user.name, "UPDATE", "products", product_id, {"name": body.name})
    return _product_to_out(product, db)



@router.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    db.delete(product)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "products", product_id, {"name": product.name})


# ---------------------------------------------------------------------------
# Master Data - Dynamic Templates
# ---------------------------------------------------------------------------

VALID_TEMPLATE_TYPES = {"WA_BLAST", "PROPOSAL_TEXT", "PROPOSAL_INTRO", "PROPOSAL_OUTRO", "FOLLOW_UP", "GENERAL"}



@router.get("/api/dynamic-templates", response_model=list[DynamicTemplateOut])
def get_dynamic_templates(
    type: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(DynamicTemplate)
    if active_only:
        query = query.filter(DynamicTemplate.is_active == True)
    if type:
        query = query.filter(DynamicTemplate.type == type)
    if category_id:
        query = query.filter(DynamicTemplate.category_id == category_id)
    templates = query.all()
    results = []
    for t in templates:
        cat_name = None
        if t.category_id:
            cat = db.query(Category).filter(Category.id == t.category_id).first()
            cat_name = cat.name if cat else None
        results.append(DynamicTemplateOut(
            id=t.id, name=t.name, type=t.type, content=t.content,
            is_active=t.is_active, category_id=t.category_id, category_name=cat_name,
        ))
    return results



@router.post("/api/dynamic-templates", response_model=DynamicTemplateOut, status_code=201)
def create_dynamic_template(body: DynamicTemplateIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if body.type not in VALID_TEMPLATE_TYPES:
        raise HTTPException(status_code=400, detail=f"Type harus salah satu dari: {', '.join(VALID_TEMPLATE_TYPES)}")
    tmpl = DynamicTemplate(
        id=str(uuid.uuid4()),
        name=body.name,
        type=body.type,
        content=body.content,
        is_active=body.is_active,
        category_id=body.category_id,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    log_audit(db, current_user.name, "CREATE", "dynamic_templates", tmpl.id, {"name": body.name, "type": body.type})
    cat_name = None
    if tmpl.category_id:
        cat = db.query(Category).filter(Category.id == tmpl.category_id).first()
        cat_name = cat.name if cat else None
    return DynamicTemplateOut(
        id=tmpl.id, name=tmpl.name, type=tmpl.type, content=tmpl.content,
        is_active=tmpl.is_active, category_id=tmpl.category_id, category_name=cat_name,
    )



@router.put("/api/dynamic-templates/{tmpl_id}", response_model=DynamicTemplateOut)
def update_dynamic_template(tmpl_id: str, body: DynamicTemplateIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    if body.type not in VALID_TEMPLATE_TYPES:
        raise HTTPException(status_code=400, detail=f"Type harus salah satu dari: {', '.join(VALID_TEMPLATE_TYPES)}")
    tmpl.name = body.name
    tmpl.type = body.type
    tmpl.content = body.content
    tmpl.is_active = body.is_active
    tmpl.category_id = body.category_id
    db.commit()
    db.refresh(tmpl)
    log_audit(db, current_user.name, "UPDATE", "dynamic_templates", tmpl_id, {"name": body.name})
    cat_name = None
    if tmpl.category_id:
        cat = db.query(Category).filter(Category.id == tmpl.category_id).first()
        cat_name = cat.name if cat else None
    return DynamicTemplateOut(
        id=tmpl.id, name=tmpl.name, type=tmpl.type, content=tmpl.content,
        is_active=tmpl.is_active, category_id=tmpl.category_id, category_name=cat_name,
    )



@router.delete("/api/dynamic-templates/{tmpl_id}", status_code=204)
def delete_dynamic_template(tmpl_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    db.delete(tmpl)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "dynamic_templates", tmpl_id, {"name": tmpl.name})


# ---------------------------------------------------------------------------
# Timeline Templates API
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# WhatsApp Numbers (Fonnte multi-device) API
# 1 token Fonnte = 1 device = 1 nomor WA. Blast campaign bisa pilih nomor.
# Tanpa pilihan -> fallback token legacy di SystemSettings (fonnte_token).
# ---------------------------------------------------------------------------

def _wa_token_preview(token: str) -> str:
    t = (token or "").strip()
    if not t:
        return ""
    if len(t) <= 8:
        return t[:2] + "****"
    return f"{t[:4]}****{t[-4:]}"


def _wa_number_out(n: WhatsAppNumber) -> WhatsAppNumberOut:
    return WhatsAppNumberOut(
        id=n.id, label=n.label or "", phone_number=n.phone_number or "",
        token_preview=_wa_token_preview(n.token), is_active=bool(n.is_active),
        created_at=n.created_at,
    )


@router.get("/api/settings/wa-numbers", response_model=list[WhatsAppNumberOut])
def list_wa_numbers(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(WhatsAppNumber).order_by(WhatsAppNumber.created_at.desc()).all()
    return [_wa_number_out(n) for n in rows]


@router.post("/api/settings/wa-numbers", response_model=WhatsAppNumberOut, status_code=201)
def create_wa_number(body: WhatsAppNumberIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    token = (body.token or "").strip()
    if not token:
        raise HTTPException(status_code=422, detail="Token Fonnte wajib diisi (1 token = 1 device = 1 nomor).")
    n = WhatsAppNumber(
        id=str(uuid.uuid4()),
        label=(body.label or "").strip() or (body.phone_number or "").strip() or "Nomor WA",
        phone_number=(body.phone_number or "").strip(),
        token=token,
        is_active=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    log_audit(db, current_user.name, "CREATE", "whatsapp_numbers", n.id, {"label": n.label, "phone_number": n.phone_number})
    return _wa_number_out(n)


@router.put("/api/settings/wa-numbers/{number_id}", response_model=WhatsAppNumberOut)
def update_wa_number(number_id: str, body: WhatsAppNumberUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    n = db.query(WhatsAppNumber).filter(WhatsAppNumber.id == number_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Nomor WA tidak ditemukan")
    if body.label is not None:
        n.label = body.label.strip()
    if body.phone_number is not None:
        n.phone_number = body.phone_number.strip()
    if body.token is not None and body.token.strip() and not body.token.startswith("****"):
        n.token = body.token.strip()
    if body.is_active is not None:
        n.is_active = bool(body.is_active)
    db.commit()
    db.refresh(n)
    log_audit(db, current_user.name, "UPDATE", "whatsapp_numbers", n.id, {"label": n.label, "is_active": bool(n.is_active)})
    return _wa_number_out(n)


@router.delete("/api/settings/wa-numbers/{number_id}", status_code=204)
def delete_wa_number(number_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    n = db.query(WhatsAppNumber).filter(WhatsAppNumber.id == number_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Nomor WA tidak ditemukan")
    used = db.query(BlastCampaign).filter(BlastCampaign.whatsapp_number_id == number_id).count()
    if used:
        raise HTTPException(
            status_code=409,
            detail=f"Nomor masih dipakai {used} campaign blast. Nonaktifkan saja (is_active=false), jangan dihapus.",
        )
    log_audit(db, current_user.name, "DELETE", "whatsapp_numbers", number_id, {"label": n.label})
    db.delete(n)
    db.commit()


@router.post("/api/settings/wa-numbers/{number_id}/test-send")
def test_wa_number(number_id: str, body: dict = Body(default=None), current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    n = db.query(WhatsAppNumber).filter(WhatsAppNumber.id == number_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Nomor WA tidak ditemukan")
    if not n.is_active:
        raise HTTPException(status_code=409, detail="Nomor sedang nonaktif")
    import httpx as _httpx
    target = (body or {}).get("target") or ADMIN_WA
    message = (body or {}).get("message") or f"Tes kirim dari ERP Kantor Teman — nomor {n.phone_number or n.label}."
    ok = _send_fonnte_sync(_normalize_phone(target), message, n.token, _httpx)
    if not ok:
        raise HTTPException(status_code=502, detail=f"Tes kirim gagal via nomor {n.phone_number or n.label}. Cek token/device di dashboard Fonnte.")
    return {"ok": True, "target": target, "number_id": n.id}
