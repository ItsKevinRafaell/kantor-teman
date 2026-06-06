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
from models import get_db, log_audit, BlastMessage, User, Lead, Contact, Project, Proposal, ProposalAnalytics, Transaction, ClientNote, ClientCredential, ClientDocument, DynamicTemplate, MessageTemplate, BrandKit, BrandAsset, Document, DocumentFolder, DocumentTemplate, GeneratedDocument, DocumentSequence, PaymentMethod, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity, WorkspaceRow
from schemas import *  # noqa: F403
from app.core.cache import cached, clear_cache_prefix
from app.services import _serialize_template, _next_doc_sequence, _peek_doc_sequence, _DOC_TYPE_PREFIX, _slugify_name
from app.services.pdf_renderer import inject_pdf_font as _inject_pdf_font
from app.services.pdf_renderer import render_pdf_from_html
from app.services.archive_service import parent_creates_cycle as _archive_parent_creates_cycle
from app.core.dependencies import (get_current_user, require_admin, UPLOADS_DIR,
    _cors_list, _get_setting, HERMES_GATEWAY_URL, _hermes_headers, _office_profile, _ads_out)
from document_template_library import get_document_template_starters

DOCUMENTS_DIR = os.path.join(UPLOADS_DIR, "generated_documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

router = APIRouter()

@router.get("/api/templates", response_model=list[TemplateOut])
def get_templates(product_category: Optional[str] = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(MessageTemplate)
    if product_category:
        query = query.filter(MessageTemplate.product_category == product_category)
    return query.all()



@router.post("/api/templates", response_model=TemplateOut, status_code=201)
def create_template(body: TemplateIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tmpl = MessageTemplate(**body.model_dump())
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl



@router.patch("/api/templates/{tmpl_id}", response_model=TemplateOut)
def update_template(tmpl_id: int, body: TemplateIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tmpl = db.query(MessageTemplate).filter(MessageTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    tmpl.product_category = body.product_category
    tmpl.variant_name = body.variant_name
    tmpl.content = body.content
    db.commit()
    db.refresh(tmpl)
    return tmpl



@router.delete("/api/templates/{tmpl_id}", status_code=204)
def delete_template(tmpl_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tmpl = db.query(MessageTemplate).filter(MessageTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    db.delete(tmpl)
    db.commit()



@router.get("/api/templates/random")
def get_random_template(
    product_category: str = Query(...),
    business_name: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates = db.query(MessageTemplate).filter(MessageTemplate.product_category == product_category).all()
    if not templates:
        templates = db.query(MessageTemplate).filter(MessageTemplate.product_category == "Lainnya").all()
    if not templates:
        return {"message": None}
    tmpl = random.choice(templates)
    return {"message": tmpl.content.replace("{{business_name}}", business_name), "variant_name": tmpl.variant_name, "template_id": tmpl.id}


# ---------------------------------------------------------------------------
# Campaign / Blast
# ---------------------------------------------------------------------------


@router.get("/api/documents", response_model=list[DocumentOut])
@cached(ttl_seconds=60, key_func=lambda r: f"cache:/api/documents")
def get_documents(
    lead_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ClientDocument)
    if lead_id == "internal":
        query = query.filter(ClientDocument.lead_id.is_(None))
    elif lead_id:
        query = query.filter(ClientDocument.lead_id == int(lead_id))
    return query.order_by(ClientDocument.created_at.desc()).all()



@router.post("/api/documents", response_model=DocumentOut, status_code=201)
def create_document(body: DocumentIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = ClientDocument(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        title=body.title,
        cloud_url=body.cloud_url,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    log_audit(db, current_user.name, "CREATE", "client_documents", doc.id, {"title": body.title})
    clear_cache_prefix("cache:/api/documents")
    return doc



@router.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    doc = db.query(ClientDocument).filter(ClientDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    log_audit(db, current_user.name, "DELETE", "client_documents", doc_id, {"title": doc.title})
    db.delete(doc)
    db.commit()
    clear_cache_prefix("cache:/api/documents")


# ---------------------------------------------------------------------------
# Brand Kit
# ---------------------------------------------------------------------------

class BrandKitUpdate(BaseModel):
    kit_name: Optional[str] = None
    is_active: Optional[bool] = None


class BrandAssetIn(BaseModel):
    asset_type: str
    name: str
    value: Optional[str] = None
    file_url: Optional[str] = None
    position: Optional[int] = 0
    asset_metadata: Optional[str] = None


def _serialize_kit(kit: BrandKit, db: Session) -> dict:
    assets = db.query(BrandAsset).filter(BrandAsset.kit_id == kit.id).order_by(BrandAsset.asset_type, BrandAsset.position).all()
    return {
        "id": kit.id,
        "kit_name": kit.kit_name,
        "is_active": kit.is_active,
        "created_at": kit.created_at,
        "assets": [
            {
                "id": a.id,
                "asset_type": a.asset_type,
                "name": a.name,
                "value": a.value,
                "file_url": a.file_url,
                "position": a.position,
                "asset_metadata": a.asset_metadata,
            }
            for a in assets
        ],
    }


def _get_active_kit(db: Session) -> BrandKit:
    kit = db.query(BrandKit).filter(BrandKit.is_active == True).first()
    if not kit:
        kit = db.query(BrandKit).first()
    if not kit:
        raise HTTPException(status_code=404, detail="Brand kit tidak ditemukan")
    return kit



@router.get("/api/brand-kit")
def get_brand_kit(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _serialize_kit(_get_active_kit(db), db)



@router.get("/api/brand-kit/public")
def get_brand_kit_public(db: Session = Depends(get_db)):
    return _serialize_kit(_get_active_kit(db), db)



@router.put("/api/brand-kit")
def update_brand_kit(body: BrandKitUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    kit = _get_active_kit(db)
    if body.kit_name is not None:
        kit.kit_name = body.kit_name
    if body.is_active is not None:
        kit.is_active = body.is_active
    db.commit()
    return _serialize_kit(kit, db)



@router.get("/api/document-templates")
def list_document_templates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    templates = db.query(DocumentTemplate).filter(DocumentTemplate.is_active == True).order_by(DocumentTemplate.name).all()
    return [_serialize_template(t) for t in templates]



@router.get("/api/document-templates/{tid}")
def get_document_template(tid: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    return _serialize_template(t)



@router.post("/api/document-templates", status_code=201)
def create_document_template(body: DocumentTemplateIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    valid_types = {"proposal_pdf", "invoice", "receipt", "kontrak", "surat_penawaran", "custom"}
    if body.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Type harus salah satu: {', '.join(valid_types)}")
    t = DocumentTemplate(
        id=str(uuid.uuid4()),
        name=body.name,
        type=body.type,
        html_template=body.html_template,
        variables=json.dumps(body.variables or []),
        is_active=body.is_active if body.is_active is not None else True,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _serialize_template(t)



@router.put("/api/document-templates/{tid}")
def update_document_template(tid: str, body: DocumentTemplateIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    t.name = body.name
    t.type = body.type
    t.html_template = body.html_template
    t.variables = json.dumps(body.variables or [])
    if body.is_active is not None:
        t.is_active = body.is_active
    db.commit()
    return _serialize_template(t)



@router.delete("/api/document-templates/{tid}", status_code=204)
def delete_document_template(tid: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    db.delete(t)
    db.commit()



@router.get("/api/generated-documents")
def list_generated_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.query(GeneratedDocument).order_by(GeneratedDocument.generated_at.desc()).all()
    return [
        {
            "id": d.id,
            "template_id": d.template_id,
            "template_name": d.template_name,
            "target_type": d.target_type,
            "target_id": d.target_id,
            "file_url": d.file_url,
            "display_filename": d.display_filename,
            "generated_at": d.generated_at,
            "generated_by": d.generated_by,
        }
        for d in docs
    ]



@router.delete("/api/documents/generated/{did}", status_code=204)
def delete_generated_document(did: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    d = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not d:
        raise HTTPException(status_code=404, detail="Document tidak ditemukan")
    if d.file_url:
        fpath = os.path.join(os.path.dirname(__file__), d.file_url.lstrip("/"))
        if os.path.exists(fpath) and os.path.realpath(fpath).startswith(os.path.realpath(DOCUMENTS_DIR)):
            try:
                os.remove(fpath)
            except Exception:
                pass
    db.delete(d)
    db.commit()


class InvoiceSequenceIn(BaseModel):
    start_from: int = Field(..., ge=1)
    template_type: str = "invoice"



@router.get("/api/documents/invoice-sequence")
def get_invoice_sequence(template_type: str = "invoice", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    seq = db.query(DocumentSequence).filter(
        DocumentSequence.target_id == "GLOBAL",
        DocumentSequence.template_type == template_type,
    ).first()
    last = seq.last_seq if seq else 0
    return {"template_type": template_type, "last_seq": last, "next_seq": last + 1}



@router.put("/api/documents/invoice-sequence")
def set_invoice_sequence(body: InvoiceSequenceIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    seq = db.query(DocumentSequence).filter(
        DocumentSequence.target_id == "GLOBAL",
        DocumentSequence.template_type == body.template_type,
    ).first()
    if not seq:
        seq = DocumentSequence(target_id="GLOBAL", template_type=body.template_type, last_seq=0)
        db.add(seq)
    seq.last_seq = body.start_from - 1
    db.commit()
    return {"template_type": body.template_type, "last_seq": seq.last_seq, "next_seq": seq.last_seq + 1}


def _build_brand_context(db: Session) -> dict:
    kit = db.query(BrandKit).filter(BrandKit.is_active == True).first() or db.query(BrandKit).first()
    ctx = {
        "logo": "", "colors": {}, "fonts": {},
        "tagline": "", "nama_perusahaan": "", "brand_name": "",
        "alamat_perusahaan": "", "phone_perusahaan": "", "email_perusahaan": ""
    }
    if not kit:
        return ctx
    # Map brand kit fields to template variables
    brand_name = getattr(kit, "brand_name", None) or kit.kit_name or ""
    ctx["nama_perusahaan"] = brand_name
    ctx["brand_name"] = brand_name
    ctx["tagline"] = getattr(kit, "tagline", None) or ""
    ctx["alamat_perusahaan"] = getattr(kit, "address", None) or ""
    ctx["phone_perusahaan"] = getattr(kit, "phone", None) or ""
    ctx["email_perusahaan"] = getattr(kit, "email", None) or ""
    assets = db.query(BrandAsset).filter(BrandAsset.kit_id == kit.id).all()
    for a in assets:
        if a.asset_type == "logo_primary" and a.file_url:
            api_base = _get_setting("app_base_url", "") or os.getenv("APP_BASE_URL", "https://api.kantorteman.my.id")
            ctx["logo"] = f'<img src="{api_base.rstrip("/")}{a.file_url}" alt="logo" style="max-height:60px"/>'
        elif a.asset_type == "color":
            ctx["colors"][a.name.lower().replace(" ", "_")] = a.value or ""
        elif a.asset_type == "font":
            ctx["fonts"][a.name.lower().replace(" ", "_")] = a.value or ""
        elif a.asset_type == "tagline" and a.value:
            ctx["tagline"] = a.value
        elif a.asset_type == "company_address" and a.value:
            ctx["alamat_perusahaan"] = a.value
        elif a.asset_type == "company_phone" and a.value:
            ctx["phone_perusahaan"] = a.value
        elif a.asset_type == "company_email" and a.value:
            ctx["email_perusahaan"] = a.value
    return ctx


def _format_date_id(value: datetime) -> str:
    months = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    return f"{value.day} {months[value.month - 1]} {value.year}"


_DATE_VALUE_KEYS = {
    "tanggal", "due_date", "valid_until", "validity",
    "tanggal_mulai", "tanggal_akhir", "expired", "expiry",
}
_DATE_VALUE_LABEL_RE = re.compile(
    r"^\s*(?:tanggal|jatuh\s+tempo|due\s+date|berlaku\s+(?:hingga|s/d)|mulai|selesai)\s*:\s*",
    re.IGNORECASE,
)
_SERVER_OWNED_DOCUMENT_KEYS = {
    "logo", "brand_name", "nama_perusahaan", "nama_klien", "perusahaan_klien",
    "alamat_perusahaan", "phone_perusahaan", "email_perusahaan", "tagline",
}


def _is_date_value_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in _DATE_VALUE_KEYS or lowered.startswith("tanggal_") or lowered.endswith("_tanggal")


def _normalize_document_variable(key: str, value):
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if _is_date_value_key(key):
        previous = None
        while previous != normalized:
            previous = normalized
            normalized = _DATE_VALUE_LABEL_RE.sub("", normalized).strip()
    return normalized


def _apply_target_company_aliases(defaults: dict, company_name: str) -> None:
    if not company_name:
        return
    defaults["nama_perusahaan"] = company_name
    defaults["nama_klien"] = company_name
    defaults["perusahaan_klien"] = company_name


def _document_number(db: Session, template_type: str, reserve: bool = False) -> str:
    prefixes = {"invoice": "INV", "receipt": "RCPT", "surat_penawaran": "SP"}
    prefix = prefixes.get(template_type)
    if not prefix:
        return ""
    seq = _next_doc_sequence(db, "GLOBAL", template_type) if reserve else _peek_doc_sequence(db, "GLOBAL", template_type)
    yyyymm = datetime.now(timezone.utc).strftime("%Y%m")
    return f"{prefix}/{yyyymm}/{seq:03d}"


def _build_default_vars(db: Session, template_type: str, target_type: Optional[str], target_id: Optional[str]) -> dict:
    today = datetime.now(timezone.utc)
    brand = _build_brand_context(db)

    defaults: dict = {
        "tanggal": _format_date_id(today),
        "logo": brand.get("logo", ""),
        "brand_name": brand.get("brand_name", ""),
        "tagline": brand.get("tagline", ""),
    }

    # Company info: prefer Brand Kit, fall back to settings for backward compat
    company_map = {
        "brand_name": ("brand_name", "company_name"),
        "alamat_perusahaan": ("alamat_perusahaan", "company_address"),
        "phone_perusahaan": ("phone_perusahaan", "company_phone"),
        "email_perusahaan": ("email_perusahaan", "company_email"),
    }
    for var_key, (brand_key, setting_key) in company_map.items():
        val = brand.get(brand_key) or _get_setting(setting_key, "")
        if val:
            defaults[var_key] = val

    lead = None
    contact = None
    project = None
    if target_id and target_type == "project":
        project = db.query(Project).filter(Project.id == target_id).first()
        if project and project.lead_id:
            lead = db.query(Lead).filter(Lead.id == project.lead_id).first()
            if lead:
                defaults["klien"] = lead.business_name or ""
                defaults["nama"] = lead.business_name or ""
                _apply_target_company_aliases(defaults, lead.business_name or "")
                defaults["alamat"] = lead.address or ""
                defaults["phone"] = lead.phone_number or ""
                defaults["layanan"] = project.name or lead.product_interest or project.service_type or ""
    elif target_id and target_id.isdigit():
        if target_type == "contact":
            contact = db.query(Contact).filter(Contact.id == int(target_id)).first()
            if contact:
                defaults["klien"] = contact.business_name or ""
                defaults["nama"] = contact.business_name or ""
                _apply_target_company_aliases(defaults, contact.business_name or "")
                defaults["alamat"] = ""
                defaults["phone"] = contact.phone_number or ""
                defaults["layanan"] = contact.purchased_product or ""
        elif target_type == "lead":
            lead = db.query(Lead).filter(Lead.id == int(target_id)).first()
            if lead:
                defaults["klien"] = lead.business_name or ""
                defaults["nama"] = lead.business_name or ""
                _apply_target_company_aliases(defaults, lead.business_name or "")
                defaults["alamat"] = lead.address or ""
                defaults["phone"] = lead.phone_number or ""
                defaults["layanan"] = lead.product_interest or ""

    defaults.setdefault("nama_perusahaan", defaults.get("brand_name", ""))

    # Resolve the service/product name for either target kind
    service_name = ""
    if lead:
        service_name = lead.product_interest or ""
    elif contact:
        service_name = contact.purchased_product or ""

    if template_type == "invoice":
        defaults["nomor_invoice"] = _document_number(db, "invoice")
        defaults["no_invoice"] = defaults["nomor_invoice"]
        defaults["due_date"] = _format_date_id(today + timedelta(days=14))
        defaults["terms"] = "Pembayaran dalam 14 hari setelah invoice diterima."
        defaults["catatan"] = "Terima kasih atas kepercayaan Anda."
        pms = db.query(PaymentMethod).filter(PaymentMethod.is_active == True).order_by(PaymentMethod.position).all()
        if pms:
            pm_lines = []
            for pm in pms:
                line = pm.name
                if pm.account_number:
                    line += f" — {pm.account_number}"
                if pm.account_name:
                    line += f" (a.n. {pm.account_name})"
                pm_lines.append(line)
            defaults["payment_info"] = "\n".join(pm_lines)
        else:
            defaults["payment_info"] = "Metode pembayaran belum diatur."

    elif template_type == "receipt":
        defaults["nomor"] = _document_number(db, "receipt")
        defaults["amount"] = ""
        defaults["payment_method"] = ""
        defaults["keterangan"] = ""

    elif template_type == "proposal_pdf":
        defaults["valid_until"] = _format_date_id(today + timedelta(days=14))
        defaults["validity"] = defaults["valid_until"]
        defaults.setdefault("scope", "")

    elif template_type == "kontrak":
        defaults["tanggal_mulai"] = _format_date_id(today)
        defaults["scope"] = ""
        defaults["terms"] = (
            "1. Pembayaran dilakukan sesuai termin yang disepakati kedua pihak.\n"
            "2. Pekerjaan di luar lingkup layanan memerlukan persetujuan dan biaya tambahan.\n"
            "3. Perubahan lingkup pekerjaan harus disepakati secara tertulis.\n"
            "4. Data dan informasi bisnis klien dijaga kerahasiaannya selama dan setelah kerja sama."
        )
        durasi_months = 1
        if project:
            durasi_months = project.contract_months or 1
            defaults["nilai_kontrak"] = f"Rp {project.nominal:,.0f}" if project.nominal else ""
        defaults["durasi"] = f"{durasi_months} bulan"
        defaults.setdefault("nilai_kontrak", "")
        if project and project.start_date:
            try:
                defaults["tanggal_mulai"] = _format_date_id(datetime.fromisoformat(project.start_date))
            except ValueError:
                pass
        if project and project.end_date:
            try:
                defaults["tanggal_akhir"] = _format_date_id(datetime.fromisoformat(project.end_date))
            except ValueError:
                pass
        if "tanggal_akhir" not in defaults:
            # tanggal_akhir = tanggal_mulai + durasi months
            end_month = (today.month - 1 + durasi_months) % 12 + 1
            end_year = today.year + (today.month - 1 + durasi_months) // 12
            from calendar import monthrange
            end_day = min(today.day, monthrange(end_year, end_month)[1])
            defaults["tanggal_akhir"] = _format_date_id(today.replace(year=end_year, month=end_month, day=end_day))

    elif template_type == "surat_penawaran":
        defaults["nomor"] = _document_number(db, "surat_penawaran")
        defaults["perihal"] = f"Penawaran Jasa {service_name}".strip()
        defaults["terms"] = "Penawaran ini berlaku 14 hari sejak tanggal surat. Harga belum termasuk pajak kecuali disebutkan lain."

    # Add default items_rows for document types that need it
    if template_type in ["invoice", "receipt", "surat_penawaran", "proposal_pdf", "kontrak"]:
        if "items_rows" not in defaults or not defaults.get("items_rows"):
            defaults["items_rows"] = '<tr><td colspan="4" style="text-align:center;color:#999;">Tidak ada item</td></tr>'

    return defaults


TRACKING_PIXEL_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")



@router.get("/api/document-templates/{template_id}/defaults")
def get_template_defaults(
    template_id: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    ttype = template.type or "custom"
    if ttype == "custom" and template.name:
        name_lower = template.name.lower()
        for known in ["invoice", "receipt", "kontrak", "surat_penawaran", "proposal_pdf"]:
            if known.replace("_", " ") in name_lower or known in name_lower:
                ttype = known
                break
    defaults = _build_default_vars(db, ttype, target_type, target_id)
    return {"defaults": defaults, "template_type": ttype}


def _build_pdf_display_name(db, template_type: str, target_type, target_id, full_vars: dict) -> str:
    # Try to build: TYPE_ClientName_InvoiceNo or TYPE_ClientName_seq_YYYYMM
    client_name = full_vars.get("klien") or full_vars.get("nama") or ""
    invoice_no = full_vars.get("nomor_invoice") or full_vars.get("no_invoice") or full_vars.get("nomor") or ""

    prefix = _DOC_TYPE_PREFIX.get(template_type, "DOC")
    client_slug = _slugify_name(client_name) if client_name else "Dokumen"

    if invoice_no:
        # Clean invoice number for filename: INV/202605/005 → INV-202605-005
        inv_slug = invoice_no.replace("/", "-").replace(" ", "-")
        return f"{prefix}_{client_slug}_{inv_slug}"

    # Fallback to seq-based name
    return _generate_document_filename(db, template_type, target_type, target_id)


def _apply_final_document_number(db: Session, template_type: str, full_vars: dict) -> None:
    number = _document_number(db, template_type, reserve=True)
    if not number:
        return
    if template_type == "invoice":
        full_vars["nomor_invoice"] = number
        full_vars["no_invoice"] = number
    else:
        full_vars["nomor"] = number


def _prepare_document_vars(db: Session, template: DocumentTemplate, body: DocumentGenerateIn, reserve_number: bool = False) -> dict:
    template_type = _document_template_type(template)
    defaults = _build_default_vars(db, template_type, body.target_type, body.target_id)
    brand_ctx = _build_brand_context(db)
    # brand_ctx first, then defaults so lead data (klien, alamat, phone, layanan)
    # takes priority over brand kit values, while brand fields (logo, tagline,
    # company info) that defaults doesn't set still come through.
    full_vars = {**brand_ctx, **defaults}
    for key, value in body.variables.items():
        value = _normalize_document_variable(key, value)
        if key in _SERVER_OWNED_DOCUMENT_KEYS and full_vars.get(key) not in (None, ""):
            continue
        if value not in (None, "") or key not in full_vars:
            full_vars[key] = value
    for key, value in list(full_vars.items()):
        full_vars[key] = _normalize_document_variable(key, value)
    if "logo" not in body.variables:
        full_vars["logo"] = brand_ctx["logo"]
    if reserve_number:
        _apply_final_document_number(db, template_type, full_vars)
    return full_vars


_BUILTIN_DOCUMENT_TEMPLATE_TYPES = {
    "Invoice": "invoice",
    "Receipt / Bukti Pembayaran": "receipt",
    "Proposal Penawaran PDF": "proposal_pdf",
    "Surat Penawaran Formal": "surat_penawaran",
    "Kontrak / MoU": "kontrak",
}

_LEGACY_DOCUMENT_TEMPLATE_MARKERS = {
    "proposal_pdf": ("{{services_html}}", "{{faqs_html}}"),
    "surat_penawaran": ("{{body}}", "{{ttd}}"),
    "kontrak": ("{{parties}}", "{{timeline}}", "{{payment_terms}}"),
}


def _document_template_type(template: DocumentTemplate) -> str:
    return _BUILTIN_DOCUMENT_TEMPLATE_TYPES.get(getattr(template, "name", ""), getattr(template, "type", None) or "custom")


def _document_template_html(template: DocumentTemplate) -> str:
    template_type = _document_template_type(template)
    html_template = template.html_template or ""
    markers = _LEGACY_DOCUMENT_TEMPLATE_MARKERS.get(template_type, ())
    is_legacy = any(marker in html_template for marker in markers)
    template_name = getattr(template, "name", "")
    has_wrong_builtin_type = template_name in _BUILTIN_DOCUMENT_TEMPLATE_TYPES and getattr(template, "type", None) != template_type
    starter = get_document_template_starters().get(template_type)
    uses_deprecated_company_scope = (
        template_name in _BUILTIN_DOCUMENT_TEMPLATE_TYPES
        and starter
        and "{{brand_name}}" not in html_template
        and "{{nama_perusahaan}}" in html_template
    )
    if (is_legacy or has_wrong_builtin_type or uses_deprecated_company_scope) and starter:
        return starter["html_template"]
    return html_template


def _render_document_html(html_template: str, full_vars: dict) -> str:
    try:
        from jinja2.sandbox import SandboxedEnvironment
        from jinja2 import Undefined

        class SilentUndefined(Undefined):
            """Renders as {{variable}} so fallback can catch it."""
            def _fail_with_undefined_error(self, *args, **kwargs):
                return f"{{{{{self._undefined_name}}}}}"
            __str__ = __repr__ = _fail_with_undefined_error

        env = SandboxedEnvironment(undefined=SilentUndefined)
        template = env.from_string(html_template)
        rendered_html = template.render(**full_vars)
        # Fallback: catch any remaining {{key}} that Jinja2 left as literal text
        for k, v in full_vars.items():
            if isinstance(v, str):
                placeholder = "{{" + k + "}}"
                rendered_html = rendered_html.replace(placeholder, v)
    except ImportError:
        rendered_html = html_template
        for k, v in full_vars.items():
            if isinstance(v, str):
                placeholder = "{{" + k + "}}"
                rendered_html = rendered_html.replace(placeholder, v)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Render template gagal: {e}")
    return rendered_html


def _visible_document_text(rendered_html: str) -> str:
    without_assets = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", rendered_html, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_assets)
    return " ".join(html_mod.unescape(without_tags).split())


def _render_document_pdf(template: DocumentTemplate, full_vars: dict) -> bytes:
    template_type = _document_template_type(template)
    rendered_html = _render_document_html(_document_template_html(template), full_vars)
    if not _visible_document_text(rendered_html):
        starter = get_document_template_starters().get(template_type)
        if starter:
            rendered_html = _render_document_html(starter["html_template"], full_vars)
    if not _visible_document_text(rendered_html):
        raise HTTPException(status_code=400, detail="Template PDF kosong. Isi HTML template terlebih dahulu.")

    try:
        return render_pdf_from_html(rendered_html, UPLOADS_DIR)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation gagal: {e}")



@router.post("/api/documents/debug-html")
def debug_document_html(body: DocumentGenerateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == body.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    full_vars = _prepare_document_vars(db, template, body)
    rendered = _render_document_html(_document_template_html(template), full_vars)
    injected = _inject_pdf_font(rendered)
    return Response(content=injected, media_type="text/html")



@router.post("/api/documents/preview")
def preview_document(request: Request, body: DocumentGenerateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    origin = request.headers.get("origin", "")
    cors_h = {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true", "Vary": "Origin"} if origin in _cors_list else {}
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == body.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan", headers=cors_h)
    try:
        full_vars = _prepare_document_vars(db, template, body)
        pdf_bytes = _render_document_pdf(template, full_vars)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail, headers=cors_h)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview gagal: {e}", headers=cors_h)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="preview.pdf"', **cors_h},
    )



@router.post("/api/documents/generate")
def generate_document(request: Request, body: DocumentGenerateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    origin = request.headers.get("origin", "")
    cors_h = {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true", "Vary": "Origin"} if origin in _cors_list else {}
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == body.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan", headers=cors_h)
    try:
        full_vars = _prepare_document_vars(db, template, body, reserve_number=True)
        pdf_bytes = _render_document_pdf(template, full_vars)
        file_id = str(uuid.uuid4())
        pdf_filename = f"{file_id}.pdf"
        pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(pdf_bytes)

        # Filename: prefer document number + client name when available
        display_name = _build_pdf_display_name(db, template.type or "custom", body.target_type, body.target_id, full_vars)
        file_url = pdf_filename
        doc = GeneratedDocument(
            id=file_id,
            template_id=template.id,
            template_name=template.name,
            target_type=body.target_type,
            target_id=body.target_id,
            variables_used=json.dumps(full_vars),
            file_url=file_url,
            display_filename=display_name,
            generated_by=current_user.name,
        )
        db.add(doc)
        db.commit()
    except HTTPException as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.detail, headers=cors_h)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"PDF generation gagal: {e}", headers=cors_h)

    return {"document_id": doc.id, "file_url": file_url, "template_name": template.name, "display_filename": display_name}



@router.get("/api/documents/{did}/download")
def download_document(did: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not doc or not doc.file_url:
        raise HTTPException(status_code=404, detail="Document tidak ditemukan")
    # Use DOCUMENTS_DIR for the path
    filename = os.path.basename(doc.file_url)
    fpath = os.path.join(DOCUMENTS_DIR, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="File tidak ada di disk")
    if doc.target_id and doc.target_id.isdigit():
        try:
            db.add(LeadActivityLog(id=str(uuid.uuid4()), lead_id=int(doc.target_id), activity_type="pdf_downloaded"))
            db.commit()
        except Exception:
            pass
    from fastapi.responses import FileResponse
    fname = doc.display_filename or (doc.template_name or "document")
    return FileResponse(fpath, media_type="application/pdf", filename=f"{fname}.pdf")



@router.post("/api/documents/{did}/email")
def email_document(did: str, body: DocumentEmailIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not doc or not doc.file_url:
        raise HTTPException(status_code=404, detail="Document tidak ditemukan")
    fpath = os.path.join(os.path.dirname(__file__), doc.file_url.lstrip("/"))
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="File tidak ada di disk")

    smtp_host = _get_setting("smtp_host", "")
    smtp_port = int(_get_setting("smtp_port", "587") or "587")
    smtp_user = _get_setting("smtp_user", "")
    smtp_pass = _get_setting("smtp_password", "")
    smtp_from = _get_setting("smtp_from", smtp_user)

    if not smtp_host or not smtp_user or not smtp_pass:
        raise HTTPException(status_code=400, detail="SMTP belum dikonfigurasi di Settings")

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = body.to_email
    brand_name = _build_brand_context(db).get("brand_name") or "Kantor Teman"
    msg["Subject"] = body.subject or f"{doc.template_name or 'Dokumen'} dari {brand_name}"
    msg.attach(MIMEText(body.body or "Terlampir dokumen yang Anda minta. Hubungi kami jika ada pertanyaan.", "plain"))

    with open(fpath, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header("Content-Disposition", f'attachment; filename="{doc.display_filename or doc.template_name or "document"}.pdf"')
        msg.attach(part)

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP send gagal: {e}")

    return {"success": True, "to": body.to_email}


# ---------------------------------------------------------------------------
# Ads Tracking Center
# ---------------------------------------------------------------------------

class AdsCampaignIn(BaseModel):
    name: str
    target_audience: str
    budget: float
    drive_link: Optional[str] = None
    status: str = "PLANNING"


class AdsCampaignUpdate(BaseModel):
    name: Optional[str] = None
    target_audience: Optional[str] = None
    budget: Optional[float] = None
    drive_link: Optional[str] = None
    leads_count: Optional[int] = None
    conversions_count: Optional[int] = None
    status: Optional[str] = None


class AdsCampaignOut(BaseModel):
    id: str
    name: str
    target_audience: str
    budget: float
    drive_link: Optional[str] = None
    leads_count: int
    conversions_count: int
    status: str
    created_at: str
    cac: Optional[float] = None
    cost_per_lead: Optional[float] = None
    model_config = {"from_attributes": True}



@router.get("/api/templates/{template_id}/stats")
def get_template_stats(template_id: str, days: int = 30, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    msgs = db.query(BlastMessage).filter(
        BlastMessage.template_id == template_id,
        BlastMessage.sent_at >= cutoff,
        BlastMessage.status != "failed",
    ).all()
    sent = len(msgs)
    delivered = sum(1 for m in msgs if m.delivered_at)
    read = sum(1 for m in msgs if m.read_at)
    replied = sum(1 for m in msgs if m.replied_at)
    lead_ids = [m.lead_id for m in msgs if m.replied_at]
    closed = db.query(Lead).filter(Lead.id.in_(lead_ids), Lead.status == "Closed/Client").count() if lead_ids else 0
    reply_rate = round(replied / sent * 100, 1) if sent else 0.0
    conversion_rate = round(closed / sent * 100, 1) if sent else 0.0
    return {
        "template_id": template_id,
        "sent": sent,
        "delivered": delivered,
        "read": read,
        "replied": replied,
        "closed": closed,
        "reply_rate": reply_rate,
        "conversion_rate": conversion_rate,
    }



@router.get("/api/archive/folders")
def list_archive_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folders = db.query(DocumentFolder).order_by(DocumentFolder.created_at).all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "parent_id": f.parent_id,
            "color": f.color,
            "created_at": f.created_at,
        }
        for f in folders
    ]



@router.post("/api/archive/folders", status_code=201)
def create_archive_folder(
    body: ArchiveFolderIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.parent_id and not db.query(DocumentFolder).filter(DocumentFolder.id == body.parent_id).first():
        raise HTTPException(status_code=400, detail="Parent folder tidak ditemukan")
    folder = DocumentFolder(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=body.name.strip(),
        parent_id=body.parent_id or None,
        color=body.color or "#6B7280",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(folder)
    db.commit()
    return {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id, "color": folder.color, "created_at": folder.created_at}



@router.put("/api/archive/folders/{folder_id}")
def update_archive_folder(
    folder_id: str,
    body: ArchiveFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    if body.name is not None:
        folder.name = body.name.strip()
    if body.color is not None:
        folder.color = body.color
    changes = body.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        if body.parent_id and not db.query(DocumentFolder).filter(DocumentFolder.id == body.parent_id).first():
            raise HTTPException(status_code=400, detail="Parent folder tidak ditemukan")
        if _archive_parent_creates_cycle(db, folder.id, body.parent_id):
            raise HTTPException(status_code=400, detail="Parent folder akan membuat siklus")
        folder.parent_id = body.parent_id or None
    db.commit()
    return {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id, "color": folder.color, "created_at": folder.created_at}



@router.delete("/api/archive/folders/{folder_id}", status_code=204)
def delete_archive_folder(
    folder_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    db.query(Document).filter(Document.folder_id == folder_id).update({"folder_id": None})
    db.query(DocumentFolder).filter(DocumentFolder.parent_id == folder_id).update({"parent_id": None})
    db.delete(folder)
    db.commit()



@router.get("/api/archive")
def list_archive_docs(
    folder_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    unfoldered: Optional[bool] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Document)
    if unfoldered:
        q = q.filter(Document.folder_id == None)
    elif folder_id is not None:
        q = q.filter(Document.folder_id == folder_id)
    if search:
        q = q.filter(Document.title.ilike(f"%{search}%"))
    docs = q.order_by(Document.updated_at.desc(), Document.created_at.desc()).limit(limit).all()
    return [_archive_doc_to_dict(d) for d in docs]



@router.post("/api/archive", status_code=201)
def create_archive_doc(
    body: ArchiveDocIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc).isoformat()
    if body.folder_id and not db.query(DocumentFolder).filter(DocumentFolder.id == body.folder_id).first():
        raise HTTPException(status_code=400, detail="Folder tidak ditemukan")
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        folder_id=body.folder_id or None,
        title=body.title.strip(),
        body=body.body or None,
        url=body.url or None,
        tags=json.dumps(body.tags or []),
        created_at=now,
        updated_at=now,
    )
    db.add(doc)
    db.commit()
    return _archive_doc_to_dict(doc)



@router.get("/api/archive/{doc_id}")
def get_archive_doc(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    return _archive_doc_to_dict(doc)



@router.put("/api/archive/{doc_id}")
def update_archive_doc(
    doc_id: str,
    body: ArchiveDocUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    changes = body.model_dump(exclude_unset=True)
    if body.title is not None:
        doc.title = body.title.strip()
    if "body" in changes:
        doc.body = body.body or None
    if "url" in changes:
        doc.url = body.url or None
    if "tags" in changes:
        doc.tags = json.dumps(body.tags or [])
    if "folder_id" in changes:
        if body.folder_id and not db.query(DocumentFolder).filter(DocumentFolder.id == body.folder_id).first():
            raise HTTPException(status_code=400, detail="Folder tidak ditemukan")
        doc.folder_id = body.folder_id or None
    doc.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return _archive_doc_to_dict(doc)



@router.delete("/api/archive/{doc_id}", status_code=204)
def delete_archive_doc(
    doc_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    db.delete(doc)
    db.commit()


def _archive_doc_to_dict(doc: Document) -> dict:
    try:
        tags = json.loads(doc.tags) if doc.tags else []
    except Exception:
        tags = []
    return {
        "id": doc.id,
        "folder_id": doc.folder_id,
        "title": doc.title,
        "body": doc.body,
        "url": doc.url,
        "tags": tags,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


# ===========================================================================
# Hermes Office Proxy
# ===========================================================================


class OfficeChatAttachment(BaseModel):
    name: str
    type: str
    data: str  # base64 data URL


class OfficeChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    attachments: Optional[List[OfficeChatAttachment]] = None


def _hermes_headers() -> dict:
    return {"X-Gateway-Token": HERMES_GATEWAY_TOKEN, "Content-Type": "application/json"}


def _office_profile(profile: str) -> str:
    return "default" if profile == "friday" else profile
