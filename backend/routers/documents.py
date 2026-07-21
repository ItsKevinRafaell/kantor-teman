import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from models import get_db, log_audit, BlastMessage, User, Lead, Contact, Project, Proposal, ProposalAnalytics, Transaction, ClientNote, ClientCredential, ClientDocument, DynamicTemplate, MessageTemplate, BrandKit, BrandAsset, Document, DocumentFolder, DocumentTemplate, GeneratedDocument, DocumentSequence, DocumentDraft, DocumentVersion, PaymentMethod, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity, WorkspaceRow, LeadActivityLog
from schemas import *  # noqa: F403
from app.core.cache import cached, clear_cache_prefix
from app.services import (
    _serialize_template,
    _next_doc_sequence,
    _peek_doc_sequence,
    _generate_document_filename,
    _DOC_TYPE_PREFIX,
    _slugify_name,
)
from app.services.pdf_renderer import inject_pdf_font as _inject_pdf_font
from app.services.pdf_renderer import render_pdf_from_html, render_pdf_from_html_with_meta, pdf_render_diagnostics
from app.services.archive_service import parent_creates_cycle as _archive_parent_creates_cycle
from app.core.dependencies import (get_current_user, require_admin, UPLOADS_DIR,
    _cors_list, _get_setting, HERMES_GATEWAY_URL, _hermes_headers, _office_profile, _ads_out,
    _detect_service_type, _detect_service_type_single_lead)
from app.constants import CLIENT_STATUS_VALUES, DOCUMENT_STATUSES, PAYMENT_STATUSES, DocumentStatus
from document_template_library import SCOPE_TEMPLATES
from app.services.sales_workflow_service import archive_generated_document
from document_template_library import get_document_template_starters, get_service_description, SERVICE_DESCRIPTIONS

DOCUMENTS_DIR = os.path.join(UPLOADS_DIR, "generated_documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
LEGACY_DOCUMENTS_DIR = os.path.join(UPLOADS_DIR, "documents")

router = APIRouter()


def _resolve_generated_document_file(file_url: str | None) -> str | None:
    if not file_url:
        return None
    path = urlparse(str(file_url).strip()).path.replace("\\", "/").lstrip("/")
    if not path:
        return None

    candidates: list[str] = []
    if path.startswith("uploads/"):
        candidates.append(os.path.join(UPLOADS_DIR, *path.split("/")[1:]))
    elif path.startswith(("generated_documents/", "documents/")):
        candidates.append(os.path.join(UPLOADS_DIR, *path.split("/")))
    else:
        filename = os.path.basename(path)
        candidates.append(os.path.join(DOCUMENTS_DIR, filename))
        candidates.append(os.path.join(LEGACY_DOCUMENTS_DIR, filename))

    uploads_root = os.path.realpath(UPLOADS_DIR)
    for candidate in candidates:
        real = os.path.realpath(candidate)
        try:
            if os.path.commonpath([uploads_root, real]) != uploads_root:
                continue
        except ValueError:
            continue
        if os.path.exists(real):
            return real
    return None

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
    brand_name: Optional[str] = None
    tagline: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    logo: Optional[str] = None
    default_document_asset_id: Optional[str] = None


# Allowed BrandAsset.asset_type values. Six logo slots — three shapes
# (primary lockup, secondary lockup, brandmark icon) × two colour variants
# (yellow, white). Existing legacy values still accepted for back-compat.
BRAND_ASSET_TYPES: list[dict] = [
    {"id": "logo_primary_yellow",  "label": "Primary lockup — kuning", "category": "logo",  "shape": "primary",   "color": "yellow"},
    {"id": "logo_primary_white",   "label": "Primary lockup — putih",  "category": "logo",  "shape": "primary",   "color": "white"},
    {"id": "logo_secondary_yellow","label": "Secondary lockup — kuning","category": "logo", "shape": "secondary", "color": "yellow"},
    {"id": "logo_secondary_white", "label": "Secondary lockup — putih","category": "logo",  "shape": "secondary", "color": "white"},
    {"id": "brandmark_yellow",     "label": "Brandmark icon — kuning", "category": "icon",  "shape": "icon",      "color": "yellow"},
    {"id": "brandmark_white",      "label": "Brandmark icon — putih",  "category": "icon",  "shape": "icon",      "color": "white"},
    # Legacy aliases — old data keeps working
    {"id": "logo_primary",         "label": "Primary lockup (legacy)",   "category": "logo",  "shape": "primary",   "color": "yellow"},
    {"id": "logo_secondary",       "label": "Secondary lockup (legacy)", "category": "logo",  "shape": "secondary", "color": "yellow"},
    {"id": "brandmark",            "label": "Brandmark / Icon (legacy)", "category": "icon",  "shape": "icon",      "color": "yellow"},
]


def _normalize_asset_type(asset_type: str) -> str:
    """Map legacy asset_type ids onto the new 6-slot naming so that rows
    uploaded by the old admin UI continue to render correctly."""
    legacy_to_new = {
        "logo_primary":   "logo_primary_yellow",
        "logo_secondary": "logo_secondary_yellow",
        "brandmark":      "brandmark_yellow",
    }
    return legacy_to_new.get(asset_type, asset_type)


class BrandAssetIn(BaseModel):
    asset_type: str
    name: str
    value: Optional[str] = None
    file_url: Optional[str] = None
    position: Optional[int] = 0
    asset_metadata: Optional[str] = None


def _serialize_kit(kit: BrandKit, db: Session) -> dict:
    assets = db.query(BrandAsset).filter(BrandAsset.kit_id == kit.id).order_by(BrandAsset.asset_type, BrandAsset.position).all()
    # Auto-pick default: admin-chosen asset → first primary-yellow → first asset.
    default_id = getattr(kit, "default_document_asset_id", None)
    if not default_id:
        for pref in ("logo_primary_yellow", "logo_primary", "logo_secondary_yellow", "logo_secondary"):
            found = next((a for a in assets if a.asset_type == pref and a.file_url), None)
            if found:
                default_id = found.id
                break
        if not default_id and assets:
            with_url = next((a for a in assets if a.file_url), None)
            if with_url:
                default_id = with_url.id

    return {
        "id": kit.id,
        "kit_name": kit.kit_name,
        "is_active": kit.is_active,
        "created_at": kit.created_at,
        "brand_name": getattr(kit, "brand_name", "") or kit.kit_name or "",
        "tagline": getattr(kit, "tagline", "") or "",
        "phone": getattr(kit, "phone", "") or "",
        "email": getattr(kit, "email", "") or "",
        "address": getattr(kit, "address", "") or "",
        "logo": getattr(kit, "logo", "") or "",
        "default_document_asset_id": default_id,
        "asset_types": BRAND_ASSET_TYPES,
        "assets": [
            {
                "id": a.id,
                "asset_type": _normalize_asset_type(a.asset_type),
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
    # Multiple active kits can exist if seeded/imported. Pick deterministically
    # by most recently created so the chosen kit is stable across requests.
    kit = db.query(BrandKit).filter(BrandKit.is_active == True).order_by(
        BrandKit.created_at.desc()
    ).first()
    if not kit:
        kit = db.query(BrandKit).order_by(BrandKit.created_at.desc()).first()
    if not kit:
        kit = BrandKit(
            id=str(uuid.uuid4()),
            kit_name="Kantor Teman",
            brand_name="Kantor Teman",
            tagline="Partner digital bisnis Anda",
            phone="",
            email="",
            address="",
            logo="",
            is_active=True,
        )
        db.add(kit)
        db.commit()
        db.refresh(kit)
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
    if body.brand_name is not None:
        kit.brand_name = body.brand_name
        if not body.kit_name:
            kit.kit_name = body.brand_name or kit.kit_name
    if body.tagline is not None:
        kit.tagline = body.tagline
    if body.phone is not None:
        kit.phone = body.phone
    if body.email is not None:
        kit.email = body.email
    if body.address is not None:
        kit.address = body.address
    if body.logo is not None:
        kit.logo = body.logo
    if body.default_document_asset_id is not None:
        kit.default_document_asset_id = body.default_document_asset_id or None
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
    valid_types = {"proposal_pdf", "invoice", "receipt", "kontrak", "mou", "surat_penawaran", "custom",
                  "kontrak_web_dev", "kontrak_seo", "kontrak_sosmed",
                  "kontrak_maintenance", "kontrak_branding", "kontrak_retainer"}
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
def list_generated_documents(
    lead_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(GeneratedDocument)
    if lead_id is not None:
        project_ids = [row[0] for row in db.query(Project.id).filter(Project.lead_id == lead_id).all()]
        contact_ids = [str(row[0]) for row in db.query(Contact.id).filter(Contact.lead_id == lead_id).all()]
        conditions = [
            (GeneratedDocument.target_type == "lead") & (GeneratedDocument.target_id == str(lead_id)),
        ]
        if project_ids:
            conditions.append((GeneratedDocument.target_type == "project") & (GeneratedDocument.target_id.in_(project_ids)))
        if contact_ids:
            conditions.append((GeneratedDocument.target_type == "contact") & (GeneratedDocument.target_id.in_(contact_ids)))
        query = query.filter(or_(*conditions))
    docs = query.order_by(GeneratedDocument.generated_at.desc()).all()
    # Pre-load targets for display name resolution
    lead_ids = {int(d.target_id) for d in docs if d.target_type == "lead" and d.target_id and str(d.target_id).isdigit()}
    contact_ids = {int(d.target_id) for d in docs if d.target_type == "contact" and d.target_id and str(d.target_id).isdigit()}
    project_ids = {d.target_id for d in docs if d.target_type == "project" and d.target_id}
    leads = {str(l.id): l.business_name for l in db.query(Lead).filter(Lead.id.in_(lead_ids)).all()} if lead_ids else {}
    contacts = {str(c.id): c.business_name for c in db.query(Contact).filter(Contact.id.in_(contact_ids)).all()} if contact_ids else {}
    projects = {p.id: p.name for p in db.query(Project).filter(Project.id.in_(project_ids)).all()} if project_ids else {}
    template_ids = {d.template_id for d in docs if d.template_id}
    templates = {t.id: t.type for t in db.query(DocumentTemplate).filter(DocumentTemplate.id.in_(template_ids)).all()} if template_ids else {}

    result = []
    for d in docs:
        display_name = None
        if d.target_type == "lead" and d.target_id:
            display_name = leads.get(d.target_id) or "Lead tidak ditemukan"
        elif d.target_type == "contact" and d.target_id:
            display_name = contacts.get(d.target_id) or "Contact tidak ditemukan"
        elif d.target_type == "project" and d.target_id:
            display_name = projects.get(d.target_id) or "Project tidak ditemukan"
        result.append({
            "id": d.id,
            "template_id": d.template_id,
            "template_name": d.template_name,
            "template_type": templates.get(d.template_id),
            "target_type": d.target_type,
            "target_id": d.target_id,
            "target_display_name": display_name,
            "file_url": d.file_url,
            "display_filename": d.display_filename,
            "status": getattr(d, "status", DocumentStatus.DRAFT),
            "payment_status": getattr(d, "payment_status", None),
            "review_notes": getattr(d, "review_notes", None),
            "approved_at": getattr(d, "approved_at", None),
            "rejected_at": getattr(d, "rejected_at", None),
            "sent_at": getattr(d, "sent_at", None),
            "signed_at": getattr(d, "signed_at", None),
            "archived_at": getattr(d, "archived_at", None),
            "generated_at": d.generated_at,
            "generated_by": d.generated_by,
        })
    return result



@router.delete("/api/documents/generated/{did}", status_code=204)
def delete_generated_document(did: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Soft-archive only — never hard-delete PDF/file so dokumen resmi tidak hilang."""
    d = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not d:
        raise HTTPException(status_code=404, detail="Document tidak ditemukan")
    now = datetime.now(timezone.utc).isoformat()
    # Soft archive: keep file on disk + DB row for audit/history
    d.status = "Diarsipkan" if "Diarsipkan" in DOCUMENT_STATUSES else (d.status or "Draft")
    d.archived_at = now
    try:
        log_audit(db, current_user.name, "ARCHIVE", "generated_documents", did, {
            "template_name": d.template_name,
            "file_url": d.file_url,
            "soft": True,
        })
    except Exception:
        pass
    db.commit()


@router.patch("/api/documents/generated/{did}/workflow")
def update_generated_document_workflow(
    did: str,
    body: DocumentWorkflowUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    if body.status not in DOCUMENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status harus salah satu: {', '.join(sorted(DOCUMENT_STATUSES))}")
    if body.payment_status is not None and body.payment_status not in PAYMENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status pembayaran harus salah satu: {', '.join(sorted(PAYMENT_STATUSES))}")

    now = datetime.now(timezone.utc).isoformat()
    doc.status = body.status
    doc.review_notes = body.review_notes
    if body.payment_status is not None:
        doc.payment_status = body.payment_status
    if body.status == "Disetujui":
        doc.approved_at = now
    elif body.status == "Ditolak":
        doc.rejected_at = now
    elif body.status == "Dikirim":
        doc.sent_at = now
    elif body.status == "Ditandatangani":
        doc.signed_at = now
    elif body.status == "Diarsipkan":
        doc.archived_at = now

    archive_doc = db.query(Document).filter(Document.source_type == "generated_document", Document.source_id == did).first()
    if archive_doc:
        archive_doc.status = body.status
        archive_doc.review_notes = body.review_notes
        archive_doc.tags = json.dumps([doc.template_name or "Dokumen", body.status])
        archive_doc.updated_at = now
    db.commit()
    log_audit(db, current_user.name, "UPDATE", "generated_documents", did, {"status": body.status, "payment_status": body.payment_status})
    return {
        "id": doc.id,
        "status": doc.status,
        "payment_status": doc.payment_status,
        "review_notes": doc.review_notes,
        "approved_at": doc.approved_at,
        "rejected_at": doc.rejected_at,
        "sent_at": doc.sent_at,
        "signed_at": doc.signed_at,
        "archived_at": doc.archived_at,
    }


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
    # Deterministic pick across multiple active kits: most recently created.
    kit = db.query(BrandKit).filter(BrandKit.is_active == True).order_by(BrandKit.created_at.desc()).first() \
        or db.query(BrandKit).order_by(BrandKit.created_at.desc()).first()
    ctx = {
        "logo": "", "logo_url": "", "colors": {}, "fonts": {},
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
    raw_email = (getattr(kit, "email", None) or "").strip()
    # Reject noreply / no-reply placeholders — never show on client-facing docs
    if raw_email and "noreply" not in raw_email.lower() and "no-reply" not in raw_email.lower():
        ctx["email_perusahaan"] = raw_email
    else:
        ctx["email_perusahaan"] = ""
    assets = db.query(BrandAsset).filter(BrandAsset.kit_id == kit.id).all()
    # company_email asset may override below; final fallback after loop

    # Choose logo for documents. Admin can pin any asset via
    # `default_document_asset_id`; otherwise fall back through the 6-slot
    # schema (primary-yellow > primary-white > brandmark-yellow > ...) and
    # finally legacy aliases (logo_primary / brandmark).
    #
    # IMPORTANT: the <img> src uses a RELATIVE "/uploads/..." path, NOT an
    # absolute https://api.kantorteman.my.id/... URL. ReportLab/WeasyPrint on
    # the sandboxed shared host cannot reach the public domain (no outbound
    # network to its own host), so an absolute URL silently fails → the logo
    # never embeds and the PDF shows a blank/orange placeholder. The relative
    # path is resolved to local disk by the renderer's uploads link callback
    # (see pdf_renderer._uploads_link_callback / _pdf_url_fetcher), which works
    # without network. The frontend preview iframe and Brand Kit page load the
    # same /uploads path same-origin, so display is unaffected.
    def _is_svg(url: str) -> bool:
        return url.lower().endswith('.svg')

    chosen_url = ""
    chosen_id = getattr(kit, "default_document_asset_id", None)
    if chosen_id:
        match = next((a for a in assets if a.id == chosen_id and a.file_url), None)
        if match:
            chosen_url = match.file_url
    if not chosen_url:
        for pref in (
            "logo_primary_yellow", "logo_primary_white",
            "logo_secondary_yellow", "logo_secondary_white",
            "brandmark_yellow", "brandmark_white",
            "logo_primary", "logo_secondary", "brandmark",
        ):
            match = next((a for a in assets if a.asset_type == pref and a.file_url), None)
            if match:
                if _is_svg(match.file_url):
                    continue
                chosen_url = match.file_url
                break
    if not chosen_url:
        match = next((a for a in assets if a.file_url and not _is_svg(a.file_url)), None)
        if match:
            chosen_url = match.file_url
    if chosen_url:
        ctx["logo"] = (
            f'<img src="{chosen_url}" alt="logo" '
            f'style="max-height:48pt;max-width:150pt;height:auto;display:block"/>'
        )
        ctx["logo_url"] = chosen_url

    # Brand accent color (yellow #f5a700) for proposal highlights
    fallback_accent = "#f5a700"
    if not ctx.get("brand_accent"):
        # prefer yellow / Optimism Yellow
        for pref in ("optimism_yellow", "yellow", "brand_yellow", "accent", "primary_yellow"):
            for key in (pref, pref.replace("_", " "), pref.replace("_", "-")):
                v = ctx.get("colors", {}).get(key.lower()) or ""
                if v and v.startswith("#"):
                    ctx["brand_accent"] = v
                    break
            if ctx.get("brand_accent"):
                break
        ctx.setdefault("brand_accent", fallback_accent)

    for a in assets:
        if a.asset_type == "color":
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
            val = (a.value or "").strip()
            if val and "noreply" not in val.lower() and "no-reply" not in val.lower():
                ctx["email_perusahaan"] = val
    # Never leave empty / noreply — templates + Reply-To use real inbox
    final = (ctx.get("email_perusahaan") or "").strip()
    if not final or "noreply" in final.lower() or "no-reply" in final.lower():
        ctx["email_perusahaan"] = "temanumkm.kita@gmail.com"
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
    # Truly server-owned - user input ignored
    # These are brand kit / document number fields, NOT client/company fields
    "logo", "brand_name", "tagline",
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
    """Set client-name aliases only. nama_perusahaan is brand-owned, not overwritten."""
    if not company_name:
        return
    defaults["nama_klien"] = company_name
    defaults["perusahaan_klien"] = company_name


def _document_number(db: Session, template_type: str, reserve: bool = False) -> str:
    prefixes = {"invoice": "INV", "receipt": "RCPT", "surat_penawaran": "SP", "proposal_pdf": "PROP", "mou": "MOU",
               "kontrak": "KONTRAK", "kontrak_web_dev": "KONTRAK-WD", "kontrak_seo": "KONTRAK-SEO",
               "kontrak_sosmed": "KONTRAK-SM", "kontrak_maintenance": "KONTRAK-MTN",
               "kontrak_branding": "KONTRAK-BRAND", "kontrak_retainer": "KONTRAK-RET"}
    prefix = prefixes.get(template_type)
    if not prefix:
        return ""
    seq = _next_doc_sequence(db, "GLOBAL", template_type) if reserve else _peek_doc_sequence(db, "GLOBAL", template_type)
    yyyymm = datetime.now(timezone.utc).strftime("%Y%m")
    return f"{prefix}/{yyyymm}/{seq:03d}"


def _apply_kontrak_dates(defaults: dict, project, today: datetime, default_months: int = 2) -> None:
    """Apply date defaults for contract templates."""
    defaults["tanggal_mulai"] = _format_date_id(today)
    defaults.setdefault("tanggal_akhir", "")
    durasi_months = default_months
    if project:
        durasi_months = project.contract_months or default_months
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
    if not defaults.get("tanggal_akhir"):
        end_month = (today.month - 1 + durasi_months) % 12 + 1
        end_year = today.year + (today.month - 1 + durasi_months) // 12
        from calendar import monthrange
        end_day = min(today.day, monthrange(end_year, end_month)[1])
        defaults["tanggal_akhir"] = _format_date_id(today.replace(year=end_year, month=end_month, day=end_day))


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
    services = []
    if target_id and target_type == "project":
        project = db.query(Project).filter(Project.id == target_id).first()
        if project:
            # Fetch services from the lead's most recent accepted proposal
            proposal = db.query(Proposal).filter(
                Proposal.lead_id == project.lead_id,
                Proposal.status == "accepted"
            ).order_by(Proposal.accepted_at.desc()).first()
            if proposal and proposal.services_detail:
                try:
                    services = json.loads(proposal.services_detail)
                except Exception:
                    services = []
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
        defaults["payment_method"] = ""
        defaults["keterangan"] = ""

    elif template_type == "proposal_pdf":
        defaults["nomor"] = _document_number(db, "proposal_pdf")
        defaults["valid_until"] = _format_date_id(today + timedelta(days=14))
        defaults["validity"] = defaults["valid_until"]
        defaults.setdefault("scope", "")

    elif template_type == "kontrak":
        _apply_kontrak_dates(defaults, project, today, 1)
        defaults["scope"] = ""
        defaults["terms"] = (
            "1. Pembayaran dilakukan sesuai termin yang disepakati kedua pihak.\n"
            "2. Pekerjaan di luar lingkup layanan memerlukan persetujuan dan biaya tambahan.\n"
            "3. Perubahan lingkup pekerjaan harus disepakati secara tertulis.\n"
            "4. Data dan informasi bisnis klien dijaga kerahasiaannya selama dan setelah kerja sama."
        )

    elif template_type == "mou":
        defaults["nomor"] = _document_number(db, "mou")
        defaults["tanggal"] = _format_date_id(today)
        defaults["tujuan"] = "Membangun kerja sama awal untuk kebutuhan layanan digital dan pemasaran bisnis."
        defaults["scope"] = "Pemetaan kebutuhan, penyusunan rekomendasi layanan, dan persiapan kerja sama lanjutan."
        defaults["tanggung_jawab_seller"] = "Menyiapkan arahan layanan, estimasi pekerjaan, jadwal tindak lanjut, dan informasi teknis yang diperlukan."
        defaults["tanggung_jawab_buyer"] = "Memberikan data bisnis yang benar, menunjuk PIC, dan meninjau rekomendasi yang disampaikan."
        defaults["durasi"] = "Berlaku sejak tanggal ditandatangani sampai ada kontrak kerja sama lanjutan atau pembatalan tertulis."
        defaults["terms"] = "Detail biaya, termin pembayaran, dan deliverable final dituangkan dalam kontrak atau invoice terpisah."

    elif template_type == "surat_penawaran":
        defaults["nomor"] = _document_number(db, "surat_penawaran")
        defaults["perihal"] = f"Penawaran Jasa {service_name}".strip()
        defaults["terms"] = "Penawaran ini berlaku 14 hari sejak tanggal surat. Harga belum termasuk pajak kecuali disebutkan lain."

    # ─── Service-Specific Contract Defaults ─────────────────────────────────────
    elif template_type == "kontrak_web_dev":
        _apply_kontrak_dates(defaults, project, today, 2)
        defaults["tech_spec"] = "Domain, hosting, tech stack, dan browser support akan disesuaikan dengan kebutuhan proyek."
        defaults["deliverables"] = "\n".join(f"- {s.get('name', '')}" for s in services) if services else "Website sesuai spesifikasi yang disepakati."
        defaults["revision_limit"] = "Maksimal 2 (dua) kali revisi gratis. Revisi tambahan akan dikenakan biaya tambahan per sesi."
        defaults["payment_schedule"] = f"DP 50% saat penandatanganan kontrak. Pelunasan saat serah terima akhir."
        defaults["milestones"] = "1. Konsep & wireframe → approval.\n2. Development sprint → demo.\n3. Testing & review.\n4. Serah terima final."
        defaults["domain_hosting"] = "Domain milik klien. Hosting dikelola oleh Pihak Pertama selama masa kontrak kecuali disepakati lain."
        defaults["bug_warranty"] = "Bug fixing gratis selama 30 hari setelah serah terima final. Keluhan di luar bug akan dikenakan biaya tambahan."
        defaults["ip_rights"] = "Semua source code dan aset desain menjadi milik klien setelah pelunasan pembayaran."
        defaults["out_of_scope"] = "Pengembangan fitur baru, redesign besar, dan integrasi pihak ketiga tidak termasuk dalam kontrak ini."

    elif template_type == "kontrak_seo":
        _apply_kontrak_dates(defaults, project, today, 6)
        defaults["target_keywords"] = "Keyword target akan disesuaikan berdasarkan riset dan disepakati kedua belah pihak."
        defaults["success_metrics"] = "Peningkatan visibilitas dan ranking untuk keyword target dalam periode kontrak. Metrik keberhasilan akan dimonitor via Google Search Console dan Google Analytics."
        defaults["disclaimer"] = "Hasil SEO bergantung pada banyak faktor eksternal (algoritma mesin pencari, kompetitor, dll). Pihak Pertama tidak menjamin ranking #1 atau hasil spesifik lainnya."
        defaults["deliverables"] = "\n".join(f"- {s.get('name', '')}" for s in services) if services else "Optimasi on-page, off-page, dan laporan bulanan."
        defaults["reporting"] = "Laporan progress bulanan dikirimkan via email. Laporan mencakup ranking keyword, traffic, dan aktivitas yang dilakukan."
        defaults["payment_schedule"] = f"Pembayaran bulanan di awal bulan. Total kontrak {defaults.get('durasi', '6 bulan')}."
        defaults["scope_change"] = "Perubahan keyword target atau arah optimasi memerlukan addendum tertulis dan penyesuaian biaya."
        defaults["out_of_scope"] = "Google Ads management, content writing untuk website, dan development tidak termasuk."

    elif template_type == "kontrak_sosmed":
        _apply_kontrak_dates(defaults, project, today, 3)
        defaults["platforms"] = "Platform yang akan dikelola akan disepakati saat kick-off. Umumnya: Instagram, TikTok, Facebook, atau sesuai kebutuhan."
        defaults["deliverables"] = "\n".join(f"- {s.get('name', '')}" for s in services) if services else "Konten feed, story, dan laporan bulanan."
        defaults["revision_limit"] = "Maksimal 1 (satu) kali revisi per konten sebelum scheduling. Revisi tambahan dikenakan biaya Rp 50.000/sesi."
        defaults["approval_flow"] = "Content calendar dikirim H-3 sebelum minggu berjalan. Klien wajib memberikan approval maximal H-1. Konten yang tidak di-approve akan di-skip."
        defaults["content_ownership"] = "Konten (caption, desain, video) menjadi milik klien setelah pembayaran. Pihak Pertama boleh menggunakan sebagai portofolio dengan izin klien."
        defaults["payment_schedule"] = f"Pembayaran bulanan di muka. Total kontrak {defaults.get('durasi', '3 bulan')}."
        defaults["platform_rules"] = "Pihak Pertama tidak bertanggung jawab atas penangguhan/penonaktifan akun akibat pelanggaran kebijakan platform oleh klien."
        defaults["escalation"] = "Untuk konten urgent (campaign, promo), klien harus inform Max H+4 jam sebelum posting. Di luar jam kerja (18.00-09.00) dan weekend, hanya untuk kondisi darurat."
        defaults["out_of_scope"] = "Pembelian ads, respond DM/chat, dan content photography/videography tidak termasuk."

    elif template_type == "kontrak_maintenance":
        _apply_kontrak_dates(defaults, project, today, 1)
        defaults["scope_included"] = "\n".join(f"- {s.get('name', '')}" for s in services) if services else "Update plugin/theme, backup mingguan, security monitoring, dan support teknis."
        defaults["sla_metrics"] = "Critical (situs down): 4 jam kerja.\nNormal (fungsi terganggu): 1x24 jam kerja.\nLow (kosmetik/minor): 3x24 jam kerja."
        defaults["coverage_hours"] = "Jam kerja: Senin-Jumat, 09.00-18.00 WIB. Di luar jam kerja hanya untuk kondisi emergency yang mempengaruhi operasional bisnis."
        defaults["payment_schedule"] = f"Pembayaran bulanan di muka."
        defaults["reporting"] = "Laporan maintenance bulanan mencakup: status backup, update yang dilakukan, dan kondisi keamanan."
        defaults["out_of_scope"] = "Website development baru, redesign, konten writing, dan hosting upgrade memerlukan addendum terpisah."
        defaults["emergency_escalation"] = "Kontak emergency: WhatsApp/SMS ke nomor yang dicantumkan saat kick-off. Emergency di luar jam kerja hanya untuk critical issues."
        defaults["ticket_resolution"] = "Issue dianggap resolved ketika klien memberikan sign-off. Jika tidak ada respon dalam 5 hari kerja, ticket akan di-closed."

    elif template_type == "kontrak_branding":
        _apply_kontrak_dates(defaults, project, today, 1)
        defaults["deliverables"] = "\n".join(f"- {s.get('name', '')}" for s in services) if services else "Logo (AI, PNG, SVG), brand guide, dan aset pendukung sesuai kesepakatan."
        defaults["concept_count"] = "3 (tiga) arah konsep awal. Klien memilih 1 arah untuk dikembangkan lebih lanjut."
        defaults["revision_limit"] = "Maksimal 3 (tiga) kali revisi gratis per konsep. Revisi di luar batas akan dikenakan biaya tambahan."
        defaults["moodboard_approval"] = "Moodboard dan brief visual harus di-approve oleh klien sebelum desain dimulai. Klien dianggap menyetujui brief apabila tidak ada Koreksi dalam 3 hari kerja."
        defaults["color_standards"] = "Standar warna akan disediakan dalam format Pantone, CMYK, HEX, dan RGB. Format final sesuai kebutuhan cetak dan digital."
        defaults["file_usage_rights"] = "File final diberikan setelah pelunasan. Hak penggunaan komersial milik klien. Pihak Pertama berhak menggunakan sebagai portofolio."
        defaults["payment_schedule"] = "DP 50% saat kick-off. Pelunasan saat serah terima final file."
        defaults["out_of_scope"] = "Website, social media management, dan material cetak tambahan memerlukan addendum terpisah."

    elif template_type == "kontrak_retainer":
        _apply_kontrak_dates(defaults, project, today, 3)
        defaults["scope_monthly"] = "\n".join(f"- {s.get('name', '')}" for s in services) if services else "Layanan retainer sesuai paket yang disepakati per bulan."
        defaults["hour_allocation"] = "Slot/jam yang tidak digunakan dalam bulan berjalan tidak dapat di akumulasi ke bulan berikutnya dan tidak dapat diuangkan."
        defaults["payment_schedule"] = f"Pembayaran bulanan di muka, sebelum tanggal 10 setiap bulannya."
        defaults["addon_rate"] = "Layanan di luar paket akan dikenakan biaya tambahan per jam atau per proyek sesuai kesepakatan."
        defaults["scope_change"] = "Penambahan atau pengurangan cakupan layanan harus disepakati melalui addendum tertulis minimal 14 hari sebelum berlakunya perubahan."
        defaults["change_request_process"] = "Permintaan layanan dikirim via email atau task board. Permintaan akan di-acknowledge dalam 1x24 jam kerja."
        defaults["termination_notice"] = "Penghentian layanan harus disampaikan secara tertulis minimal 30 (tiga puluh) hari kalender sebelum akhir bulan berjalan."
        defaults["reporting"] = "Laporan progress bulanan dikirimkan via email sebelum tanggal 5 bulan berikutnya."

    # Add default items_rows for document types that need it
    # Resolve service type from project or lead for smart defaults
    service_type = ""
    if project:
        st_raw = getattr(project, "service_type", "") or ""
        service_types = [s.strip() for s in st_raw.split(",") if s.strip()]
        service_type = service_types[0] if service_types else ""
    elif lead:
        st = _detect_service_type_single_lead(lead)
        service_type = st if st else ""
    elif contact:
        st = _detect_service_type_single_lead(contact)
        service_type = st if st else ""

    # Apply service descriptions as defaults for contract/proposal templates
    if service_type and template_type.startswith("kontrak"):
        svc_desc = get_service_description(service_type)
        if svc_desc:
            for k, v in svc_desc.items():
                if k in defaults and not defaults[k]:
                    defaults[k] = v
                elif k not in defaults:
                    defaults[k] = v

    # Auto-populate scope from SCOPE_TEMPLATES based on service_type
    if service_type and service_type in SCOPE_TEMPLATES:
        scope_template = SCOPE_TEMPLATES[service_type]
        if "scope" not in defaults or not defaults.get("scope"):
            defaults["scope"] = scope_template["scope"]

    # Auto-populate line items from matching products
    if template_type in ["invoice", "receipt", "surat_penawaran", "proposal_pdf", "kontrak"]:
        if "items_rows" not in defaults or not defaults.get("items_rows"):
            # Try to find matching products based on service_type or product_interest
            from models import Product, Category
            matched_products = []

            # Determine search criteria
            search_name = ""
            if lead and lead.product_interest:
                search_name = lead.product_interest
            elif contact and contact.purchased_product:
                search_name = contact.purchased_product
            elif project and project.service_type:
                search_name = project.service_type

            # Query products matching the service type
            if search_name:
                # Try exact category match first
                category = db.query(Category).filter(
                    (Category.name.ilike(f"%{search_name}%")) |
                    (Category.description.ilike(f"%{search_name}%"))
                ).first()

                if category:
                    matched_products = db.query(Product).filter(
                        Product.category_id == category.id,
                        Product.is_active == True
                    ).order_by(Product.base_price.asc()).all()
                else:
                    # Fallback: search by product name
                    matched_products = db.query(Product).filter(
                        (Product.name.ilike(f"%{search_name}%")) |
                        (Product.description.ilike(f"%{search_name}%")),
                        Product.is_active == True
                    ).order_by(Product.base_price.asc()).limit(3).all()

            # Generate HTML table rows from matched products
            if matched_products:
                rows = []
                for p in matched_products:
                    # Parse features JSON
                    features = []
                    if p.features:
                        try:
                            features = json.loads(p.features)
                        except:
                            features = []

                    # Build description from features — use <br/> for PDF compatibility
                    desc = "<br/>".join(f"• {f}" for f in features[:5]) if features else (p.description or "").replace("\n", "<br/>")

                    # Format price
                    price_formatted = f"Rp {p.base_price:,.0f}".replace(",", ".")

                    # Generate row HTML
                    row = f'''<tr>
<td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">
<strong>{p.name}</strong>
<div style="margin-top:3px;color:#6b7280;font-size:11px;line-height:1.45">{desc}</div>
</td>
<td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:center">1</td>
<td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right">{price_formatted}</td>
<td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600">{price_formatted}</td>
</tr>'''
                    rows.append(row)

                defaults["items_rows"] = "\n".join(rows)
            else:
                # Fallback to empty state
                defaults["items_rows"] = '<tr><td colspan="4" style="text-align:center;color:#999;">Tidak ada item</td></tr>'

    return defaults


TRACKING_PIXEL_PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")



@router.get("/api/document-templates/{template_id}/defaults")
@router.get("/api/document-templates/{template_id}/defaults/")
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
        for known in ["invoice", "receipt", "kontrak", "mou", "surat_penawaran", "proposal_pdf"]:
            if known.replace("_", " ") in name_lower or known in name_lower:
                ttype = known
                break
    defaults = _build_default_vars(db, ttype, target_type, target_id)
    return {"defaults": defaults, "template_type": ttype}


@router.get("/api/document-scope-templates")
def list_scope_templates(current_user: User = Depends(get_current_user)):
    """List available scope templates per service type."""
    from document_template_library import SCOPE_TEMPLATES
    return [
        {"service_type": k, "name": v["name"], "scope": v["scope"]}
        for k, v in SCOPE_TEMPLATES.items()
    ]


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


def _prepare_document_vars(
    db: Session,
    template: DocumentTemplate,
    body: DocumentGenerateIn,
    reserve_number: bool = False,
    allow_db_defaults: bool = False,
) -> dict:
    """Prepare variables for preview/generate. User input (body.variables) is source of truth.

    Server-owned keys (logo, brand_name, tagline, tanggal) come from brand context or direct computation.
    Client/company/service fields come exclusively from body.variables — NO re-query of target DB.

    allow_db_defaults=True is ONLY for /defaults prefill endpoint. Preview/generate must NOT
    query target DB for client/company/service fields.
    """
    template_type = _document_template_type(template)
    brand_ctx = _build_brand_context(db)
    today = datetime.now(timezone.utc)
    # Start with brand context + generic server-computed fields
    full_vars = dict(brand_ctx)
    full_vars["tanggal"] = _format_date_id(today)
    # Always seed with document-type defaults — even when no target is provided.
    # Without this, optional fields (terms, catatan, payment_info, scope, ...) leak
    # through Jinja Undefined as literal "{{key}}" placeholders into the rendered
    # PDF, producing garbage text like "{terms}" or "{catatan}".
    defaults = _build_default_vars(db, template_type, None, None)
    for k, v in defaults.items():
        if k not in full_vars:
            full_vars[k] = v
    # Only call _build_default_vars when allow_db_defaults=True (prefill endpoint).
    # Preview/generate MUST NOT re-query target DB for client/company/service fields.
    if allow_db_defaults and body.target_id and body.target_type:
        defaults = _build_default_vars(db, template_type, body.target_type, body.target_id)
        for k, v in defaults.items():
            if k not in full_vars:
                full_vars[k] = v
    # User variables override defaults for client/company/service fields.
    # Empty string from frontend means "I haven't touched this field" — do NOT
    # override a non-empty backend default with it.  Only override when the user
    # explicitly provides a non-empty value, or when the field has no default yet.
    for key, value in body.variables.items():
        value = _normalize_document_variable(key, value)
        # Server-owned: only override if currently empty/none
        if key in _SERVER_OWNED_DOCUMENT_KEYS:
            if full_vars.get(key) in (None, ""):
                full_vars[key] = value
            continue
        # If user sent empty string AND backend already has a non-empty default,
        # keep the default — the user simply hasn't edited this field yet.
        if (value is None or value == "") and full_vars.get(key):
            continue
        # All other fields: set when user provides a value
        full_vars[key] = value if value is not None else ""
    for key, value in list(full_vars.items()):
        full_vars[key] = _normalize_document_variable(key, value)
    if "logo" not in body.variables or body.variables.get("logo", "").strip() == "":
        full_vars["logo"] = brand_ctx.get("logo", "")
    if reserve_number:
        _apply_final_document_number(db, template_type, full_vars)
    return full_vars


_BUILTIN_DOCUMENT_TEMPLATE_TYPES = {
    "Invoice": "invoice",
    "Receipt / Bukti Pembayaran": "receipt",
    "Proposal Penawaran PDF": "proposal_pdf",
    "Surat Penawaran Formal": "surat_penawaran",
    "Kontrak / MoU": "kontrak",
    "Kontrak Kerja Sama": "kontrak",
    "MOU Kerja Sama": "mou",
    # Service-specific contract addendum templates
    "Kontrak — Website Development": "kontrak_web_dev",
    "Kontrak — SEO & Google Business": "kontrak_seo",
    "Kontrak — Social Media Management": "kontrak_sosmed",
    "Kontrak — Maintenance & Support": "kontrak_maintenance",
    "Kontrak — Branding & Visual Identity": "kontrak_branding",
    "Kontrak — Paket Retainer Bulanan": "kontrak_retainer",
}

_LEGACY_DOCUMENT_TEMPLATE_MARKERS = {
    "proposal_pdf": ("{{services_html}}", "{{faqs_html}}"),
    "surat_penawaran": ("{{body}}", "{{ttd}}"),
    "kontrak": ("{{parties}}", "{{timeline}}", "{{payment_terms}}"),
    "mou": ("{{tujuan}}", "{{tanggung_jawab_seller}}", "{{tanggung_jawab_buyer}}"),
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
    # Built-in proposal template: always prefer code starter so design polish
    # (header-band, accent bar) ships without a manual DB seed step.
    uses_old_proposal_layout = (
        template_type == "proposal_pdf"
        and starter
        and "header-band" not in html_template
    )
    if (is_legacy or has_wrong_builtin_type or uses_deprecated_company_scope or uses_old_proposal_layout) and starter:
        return starter["html_template"]
    return html_template


def _apply_placeholders(html: str, full_vars: dict) -> str:
    """Substitute both {{key}} and single-brace {key} placeholders.

    Starter templates use single-brace {key}; Jinja2 only renders {{key}}, so
    single-brace tokens survive untouched and appear raw in the output. Replace
    every known variable's single-brace token explicitly (negative lookarounds
    so the inner {key} of a {{key}} token is left alone).

    For text values containing newlines, convert \\n to <br> so they render
    correctly in PDF. Skip this for HTML values (detected by presence of < tag).
    """
    for k, v in full_vars.items():
        if not isinstance(v, str):
            continue
        # Convert newlines to <br> for text values (but not HTML)
        if "\n" in v and "<" not in v:
            v = v.replace("\n", "<br>")
        html = html.replace("{{" + k + "}}", v)
        html = re.sub(r"(?<!\{)\{" + re.escape(k) + r"\}(?!\})", lambda _: v, html)
    return html


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
        rendered_html = _apply_placeholders(rendered_html, full_vars)
    except ImportError:
        rendered_html = _apply_placeholders(html_template, full_vars)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Render template gagal: {e}")
    return rendered_html


def _visible_document_text(rendered_html: str) -> str:
    without_assets = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", rendered_html, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_assets)
    return " ".join(html_mod.unescape(without_tags).split())


def _render_document_pdf(template: DocumentTemplate, full_vars: dict) -> tuple[bytes, str]:
    template_type = _document_template_type(template)
    rendered_html = _render_document_html(_document_template_html(template), full_vars)
    if not _visible_document_text(rendered_html):
        starter = get_document_template_starters().get(template_type)
        if starter:
            rendered_html = _render_document_html(starter["html_template"], full_vars)
    if not _visible_document_text(rendered_html):
        raise HTTPException(status_code=400, detail="Template PDF kosong. Isi HTML template terlebih dahulu.")

    try:
        pdf, renderer = render_pdf_from_html_with_meta(rendered_html, UPLOADS_DIR, template_type=template_type)
        return pdf, renderer
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation gagal: {e}")



@router.post("/api/documents/preview-debug")
def preview_debug(body: DocumentGenerateIn, current_user: User = Depends(get_current_user)):
    """Debug endpoint: echoes back exactly what the frontend sends."""
    non_empty = {k: str(v)[:200] for k, v in body.variables.items() if v}
    empty = [k for k, v in body.variables.items() if not v]
    return {"template_id": body.template_id, "target_type": body.target_type, "target_id": body.target_id,
            "vars_total": len(body.variables), "non_empty_count": len(non_empty), "empty_count": len(empty),
            "non_empty": non_empty, "empty_keys": empty}


@router.post("/api/documents/preview-debug")
def preview_debug(body: DocumentGenerateIn, current_user: User = Depends(get_current_user)):
    """Echo back what the frontend sends."""
    non_empty = {k: str(v)[:200] for k, v in body.variables.items() if v}
    empty = [k for k, v in body.variables.items() if not v]
    return JSONResponse({"template_id": body.template_id, "target_type": body.target_type,
                         "target_id": body.target_id, "vars_total": len(body.variables),
                         "non_empty": non_empty, "empty_keys": empty})


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
@router.post("/api/documents/preview/")
def preview_document(request: Request, body: DocumentGenerateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    origin = request.headers.get("origin", "")
    cors_h = {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true", "Vary": "Origin"} if origin in _cors_list else {}
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == body.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan", headers=cors_h)
    try:
        full_vars = _prepare_document_vars(db, template, body)
        pdf_bytes, pdf_renderer = _render_document_pdf(template, full_vars)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail, headers=cors_h)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview gagal: {e}", headers=cors_h)
    preview_name = _build_pdf_display_name(db, _document_template_type(template), body.target_type, body.target_id, full_vars) or template.name or "Preview"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{preview_name}.pdf"',
            "X-Pdf-Renderer": pdf_renderer,
            **cors_h,
        },
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
        pdf_bytes, _ = _render_document_pdf(template, full_vars)
        file_id = str(uuid.uuid4())
        pdf_filename = f"{file_id}.pdf"
        pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(pdf_bytes)

        # Filename: prefer document number + client name when available
        display_name = _build_pdf_display_name(db, _document_template_type(template), body.target_type, body.target_id, full_vars)
        file_url = f"/uploads/generated_documents/{pdf_filename}"
        doc = GeneratedDocument(
            id=file_id,
            template_id=template.id,
            template_name=template.name,
            target_type=body.target_type,
            target_id=body.target_id,
            variables_used=json.dumps(full_vars),
            file_url=file_url,
            display_filename=display_name,
            status=DocumentStatus.DRAFT,
            payment_status="Belum Dibayar" if _document_template_type(template) == "invoice" else None,
            generated_by=current_user.name,
        )
        db.add(doc)
        db.flush()
        try:
            archive_generated_document(
                db,
                doc,
                display_name,
                full_vars.get("klien") or full_vars.get("nama") or "Klien",
                full_vars.get("layanan") or body.target_type or "Dokumen",
                template.name or _document_template_type(template),
            )
        except Exception as archive_err:
            print(f"[GENERATED_DOC_ARCHIVE] skip: {archive_err}", flush=True)
        db.commit()

        # Clean up matching draft after successful generation
        try:
            db.query(DocumentDraft).filter(
                DocumentDraft.user_id == current_user.id,
                DocumentDraft.template_id == body.template_id,
                DocumentDraft.target_type == body.target_type,
                DocumentDraft.target_id == body.target_id,
            ).delete(synchronize_session=False)
            db.commit()
        except Exception:
            pass  # Draft cleanup is non-critical
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
    fpath = _resolve_generated_document_file(doc.file_url)
    if not fpath:
        raise HTTPException(status_code=404, detail="File tidak ada di disk")
    if doc.target_id and doc.target_id.isdigit():
        lead_id = int(doc.target_id)
        # Check if lead exists before logging activity
        if db.query(Lead).filter(Lead.id == lead_id).first():
            try:
                db.add(LeadActivityLog(id=str(uuid.uuid4()), lead_id=lead_id, activity_type="pdf_downloaded"))
                db.commit()
            except Exception:
                db.rollback()
    from fastapi.responses import FileResponse
    fname = doc.display_filename or (doc.template_name or "document")
    return FileResponse(fpath, media_type="application/pdf", filename=f"{fname}.pdf")



@router.post("/api/documents/{did}/email")
def email_document(did: str, body: DocumentEmailIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not doc or not doc.file_url:
        raise HTTPException(status_code=404, detail="Document tidak ditemukan")
    fpath = _resolve_generated_document_file(doc.file_url)
    if not fpath:
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

    brand_ctx = _build_brand_context(db)
    brand_name = brand_ctx.get("brand_name") or "Kantor Teman"
    brand_email = (brand_ctx.get("email_perusahaan") or "").strip() or "temanumkm.kita@gmail.com"

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = body.to_email
    # Reply-To uses BrandKit email (never noreply) so clients reply to real inbox
    msg["Reply-To"] = brand_email
    msg["Subject"] = body.subject or f"{doc.template_name or 'Dokumen'} dari {brand_name}"
    default_body = (
        f"Terlampir dokumen yang Anda minta.\n\n"
        f"Hubungi kami di {brand_email} jika ada pertanyaan.\n\n"
        f"— {brand_name}"
    )
    msg.attach(MIMEText(body.body or default_body, "plain"))

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
# Document Drafts (pre-generate)
# ---------------------------------------------------------------------------

@router.get("/api/document-drafts")
def list_document_drafts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List current user's drafts."""
    drafts = db.query(DocumentDraft).filter(
        DocumentDraft.user_id == current_user.id
    ).order_by(DocumentDraft.updated_at.desc() if DocumentDraft.updated_at is not None else DocumentDraft.created_at.desc()).all()
    result = []
    for d in drafts:
        try:
            vars_json = json.loads(d.variables_json) if d.variables_json else {}
        except Exception:
            vars_json = {}
        try:
            line_items = json.loads(d.line_items_json) if d.line_items_json else {}
        except Exception:
            line_items = {}
        result.append({
            "id": d.id,
            "template_id": d.template_id,
            "template_name": d.template_name,
            "target_type": d.target_type,
            "target_id": d.target_id,
            "variables_json": vars_json,
            "line_items_json": line_items,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        })
    return result


@router.get("/api/document-drafts/{draft_id}")
def get_document_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single draft for resume."""
    d = db.query(DocumentDraft).filter(
        DocumentDraft.id == draft_id,
        DocumentDraft.user_id == current_user.id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Draft tidak ditemukan")
    try:
        vars_json = json.loads(d.variables_json) if d.variables_json else {}
    except Exception:
        vars_json = {}
    try:
        line_items = json.loads(d.line_items_json) if d.line_items_json else {}
    except Exception:
        line_items = {}
    return {
        "id": d.id,
        "template_id": d.template_id,
        "template_name": d.template_name,
        "target_type": d.target_type,
        "target_id": d.target_id,
        "variables_json": vars_json,
        "line_items_json": line_items,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


@router.post("/api/document-drafts", status_code=201)
def create_or_update_document_draft(
    body: DocumentDraftIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a draft. If body.id is set, force-update that draft.
    Otherwise upsert by template_id+target combo."""
    now = datetime.now(timezone.utc).isoformat()

    existing = None
    # 1. If draft id is provided, update that specific draft
    if body.id:
        existing = db.query(DocumentDraft).filter(
            DocumentDraft.id == body.id,
            DocumentDraft.user_id == current_user.id,
        ).first()

    # 2. Otherwise, try to find by template+target combo
    if not existing and body.template_id:
        existing = db.query(DocumentDraft).filter(
            DocumentDraft.user_id == current_user.id,
            DocumentDraft.template_id == body.template_id,
            DocumentDraft.target_type == body.target_type,
            DocumentDraft.target_id == body.target_id,
        ).first()

    if existing:
        existing.variables_json = json.dumps(body.variables_json)
        existing.line_items_json = json.dumps(body.line_items_json) if body.line_items_json else None
        existing.updated_at = now
        if body.template_name:
            existing.template_name = body.template_name
        if body.target_type is not None:
            existing.target_type = body.target_type
        if body.target_id is not None:
            existing.target_id = body.target_id
        draft = existing
        log_audit(db, current_user.name, "UPDATE", "document_drafts", draft.id, {"template_name": draft.template_name})
    else:
        draft = DocumentDraft(
            id=body.id or str(uuid.uuid4()),
            user_id=current_user.id,
            template_id=body.template_id,
            template_name=body.template_name,
            target_type=body.target_type,
            target_id=body.target_id,
            variables_json=json.dumps(body.variables_json),
            line_items_json=json.dumps(body.line_items_json) if body.line_items_json else None,
            created_at=now,
            updated_at=now,
        )
        db.add(draft)
        log_audit(db, current_user.name, "CREATE", "document_drafts", draft.id, {"template_name": draft.template_name})

    db.commit()
    try:
        vars_json = json.loads(draft.variables_json) if draft.variables_json else {}
    except Exception:
        vars_json = {}
    return {
        "id": draft.id,
        "template_id": draft.template_id,
        "template_name": draft.template_name,
        "target_type": draft.target_type,
        "target_id": draft.target_id,
        "variables_json": vars_json,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
    }


@router.delete("/api/document-drafts/{draft_id}", status_code=204)
def delete_document_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a draft."""
    d = db.query(DocumentDraft).filter(
        DocumentDraft.id == draft_id,
        DocumentDraft.user_id == current_user.id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Draft tidak ditemukan")
    db.delete(d)
    db.commit()


# ---------------------------------------------------------------------------
# Document Edit + Version History (post-generate)
# ---------------------------------------------------------------------------

@router.post("/api/documents/generated/{did}/edit")
def edit_generated_document(
    did: str,
    body: DocumentEditIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit a generated document's variables and/or HTML content.
    Creates a version snapshot before applying changes."""
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    if not body.variables and not body.html_content:
        raise HTTPException(status_code=400, detail="Tidak ada perubahan yang diberikan")

    now = datetime.now(timezone.utc).isoformat()

    # ── Step 1: Create version snapshot of current state ──
    last_version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == did
    ).order_by(DocumentVersion.version_number.desc()).first()
    next_version = (last_version.version_number + 1) if last_version else 1

    current_vars = {}
    try:
        current_vars = json.loads(doc.variables_used) if doc.variables_used else {}
    except Exception:
        current_vars = {}

    # Render current HTML for snapshot
    current_html = None
    if doc.template_id:
        template = db.query(DocumentTemplate).filter(DocumentTemplate.id == doc.template_id).first()
        if template:
            try:
                rendered = _render_document_html(_document_template_html(template), current_vars)
                current_html = rendered
            except Exception:
                pass

    version = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=did,
        version_number=next_version,
        variables_json=json.dumps(current_vars),
        html_content=current_html,
        change_summary=body.change_summary or "Edit dokumen",
        created_at=now,
        created_by=current_user.name,
    )
    db.add(version)

    # ── Step 2: Apply variable changes ──
    if body.variables:
        old_vars = dict(current_vars)
        current_vars.update(body.variables)
        # Re-render PDF from template with new variables
        if doc.template_id:
            template = db.query(DocumentTemplate).filter(DocumentTemplate.id == doc.template_id).first()
            if template:
                try:
                    pdf_bytes = _render_document_pdf(template, current_vars)
                    pdf_filename = f"{str(uuid.uuid4())}.pdf"
                    pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
                    with open(pdf_path, "wb") as pdf_file:
                        pdf_file.write(pdf_bytes)
                    # Remove old PDF
                    old_path = _resolve_generated_document_file(doc.file_url)
                    if old_path and os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except Exception:
                            pass
                    doc.file_url = f"/uploads/generated_documents/{pdf_filename}"
                    doc.variables_used = json.dumps(current_vars)
                    doc.is_edited = True
                except HTTPException as e:
                    db.rollback()
                    raise HTTPException(status_code=e.status_code, detail=e.detail)
                except Exception as e:
                    db.rollback()
                    raise HTTPException(status_code=500, detail=f"Gagal regenerate PDF: {e}")

    # ── Step 3: Apply direct HTML content edit ──
    if body.html_content:
        doc.edited_html = body.html_content
        doc.is_edited = True
        # Also regenerate PDF from edited HTML
        try:
            injected = _inject_pdf_font(body.html_content)
            edit_template = db.query(DocumentTemplate).filter(DocumentTemplate.id == doc.template_id).first()
            edit_template_type = _document_template_type(edit_template) if edit_template else None
            pdf_bytes = render_pdf_from_html(injected, UPLOADS_DIR, template_type=edit_template_type)
            pdf_filename = f"{str(uuid.uuid4())}.pdf"
            pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
            with open(pdf_path, "wb") as pdf_file:
                pdf_file.write(pdf_bytes)
            # Remove old PDF
            old_path = _resolve_generated_document_file(doc.file_url)
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass
            doc.file_url = f"/uploads/generated_documents/{pdf_filename}"
        except HTTPException as e:
            db.rollback()
            raise HTTPException(status_code=e.status_code, detail=e.detail)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Gagal regenerate PDF dari HTML: {e}")

    doc.updated_at = now
    db.commit()
    log_audit(db, current_user.name, "EDIT", "generated_documents", did,
              {"version": next_version, "change_summary": body.change_summary})

    return {
        "id": doc.id,
        "file_url": doc.file_url,
        "is_edited": doc.is_edited,
        "version": next_version,
    }


@router.get("/api/documents/generated/{did}/versions")
def list_document_versions(
    did: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List version history for a generated document."""
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == did
    ).order_by(DocumentVersion.version_number.desc()).all()

    result = []
    for v in versions:
        try:
            vars_json = json.loads(v.variables_json) if v.variables_json else {}
        except Exception:
            vars_json = {}
        result.append({
            "id": v.id,
            "version_number": v.version_number,
            "variables_json": vars_json,
            "html_content": v.html_content,
            "change_summary": v.change_summary,
            "created_at": v.created_at,
            "created_by": v.created_by,
        })

    # Add v0 = original
    try:
        orig_vars = json.loads(doc.variables_used) if doc.variables_used else {}
    except Exception:
        orig_vars = {}
    result.append({
        "id": "original",
        "version_number": 0,
        "variables_json": orig_vars,
        "html_content": None,
        "change_summary": "Asli (saat generate)",
        "created_at": doc.generated_at,
        "created_by": doc.generated_by,
    })
    return result


@router.post("/api/documents/generated/{did}/versions/{vid}/rollback")
def rollback_document_version(
    did: str,
    vid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rollback a document to a previous version."""
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == did).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    now = datetime.now(timezone.utc).isoformat()

    if vid == "original":
        # Rollback to original (re-generate from template with original variables)
        if not doc.template_id:
            raise HTTPException(status_code=400, detail="Tidak ada template untuk rollback")
        template = db.query(DocumentTemplate).filter(DocumentTemplate.id == doc.template_id).first()
        if not template:
            raise HTTPException(status_code=400, detail="Template tidak ditemukan")

        try:
            orig_vars = json.loads(doc.variables_used) if doc.variables_used else {}
        except Exception:
            raise HTTPException(status_code=400, detail="Variabel tidak bisa dibaca")

        try:
            pdf_bytes = _render_document_pdf(template, orig_vars)
            pdf_filename = f"{str(uuid.uuid4())}.pdf"
            pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
            with open(pdf_path, "wb") as pdf_file:
                pdf_file.write(pdf_bytes)
            doc.file_url = f"/uploads/generated_documents/{pdf_filename}"
            doc.edited_html = None
            doc.is_edited = False
        except HTTPException as e:
            db.rollback()
            raise HTTPException(status_code=e.status_code, detail=e.detail)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Gagal rollback: {e}")

    else:
        version = db.query(DocumentVersion).filter(
            DocumentVersion.id == vid,
            DocumentVersion.document_id == did,
        ).first()
        if not version:
            raise HTTPException(status_code=404, detail="Versi tidak ditemukan")

        try:
            v_vars = json.loads(version.variables_json) if version.variables_json else {}
        except Exception:
            raise HTTPException(status_code=400, detail="Variabel versi tidak bisa dibaca")

        if version.html_content:
            # Rollback to HTML snapshot
            try:
                injected = _inject_pdf_font(version.html_content)
                rb_template = db.query(DocumentTemplate).filter(DocumentTemplate.id == doc.template_id).first()
                rb_template_type = _document_template_type(rb_template) if rb_template else None
                pdf_bytes = render_pdf_from_html(injected, UPLOADS_DIR, template_type=rb_template_type)
                pdf_filename = f"{str(uuid.uuid4())}.pdf"
                pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
                with open(pdf_path, "wb") as pdf_file:
                    pdf_file.write(pdf_bytes)
                doc.file_url = f"/uploads/generated_documents/{pdf_filename}"
                doc.edited_html = version.html_content
                doc.is_edited = True
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Gagal rollback: {e}")
        elif doc.template_id:
            # Rollback to variables snapshot, re-render from template
            template = db.query(DocumentTemplate).filter(DocumentTemplate.id == doc.template_id).first()
            if not template:
                raise HTTPException(status_code=400, detail="Template tidak ditemukan")
            try:
                pdf_bytes = _render_document_pdf(template, v_vars)
                pdf_filename = f"{str(uuid.uuid4())}.pdf"
                pdf_path = os.path.join(DOCUMENTS_DIR, pdf_filename)
                with open(pdf_path, "wb") as pdf_file:
                    pdf_file.write(pdf_bytes)
                doc.file_url = f"/uploads/generated_documents/{pdf_filename}"
                doc.variables_used = json.dumps(v_vars)
                doc.edited_html = None
                doc.is_edited = False
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Gagal rollback: {e}")

    doc.updated_at = now
    db.commit()
    log_audit(db, current_user.name, "ROLLBACK", "generated_documents", did,
              {"rollback_to_version": vid})

    return {
        "id": doc.id,
        "file_url": doc.file_url,
        "is_edited": doc.is_edited,
        "rollback_to": vid,
    }


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
    closed = db.query(Lead).filter(Lead.id.in_(lead_ids), Lead.status.in_(CLIENT_STATUS_VALUES)).count() if lead_ids else 0
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
    changes = body.model_dump(exclude_unset=True)

    if "name" in changes and body.name is not None:
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Nama folder tidak boleh kosong")
        folder.name = name
    if "color" in changes and body.color is not None:
        color = (body.color or "").strip() or "#6B7280"
        if len(color) > 20:
            raise HTTPException(status_code=400, detail="Warna folder tidak valid")
        folder.color = color
    if "parent_id" in changes:
        parent_id = body.parent_id or None
        if parent_id == folder.id:
            raise HTTPException(status_code=400, detail="Folder tidak bisa jadi parent dirinya sendiri")
        if parent_id and not db.query(DocumentFolder).filter(DocumentFolder.id == parent_id).first():
            raise HTTPException(status_code=400, detail="Parent folder tidak ditemukan")
        if parent_id and _archive_parent_creates_cycle(db, folder.id, parent_id):
            raise HTTPException(status_code=400, detail="Parent folder akan membuat siklus")
        folder.parent_id = parent_id
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan folder: {exc}")
    return {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id, "color": folder.color, "created_at": folder.created_at}


def _archive_folder_descendant_ids(db: Session, folder_id: str) -> list[str]:
    folders = db.query(DocumentFolder.id, DocumentFolder.parent_id).all()
    children: dict[str | None, list[str]] = defaultdict(list)
    for fid, parent_id in folders:
        children[parent_id].append(fid)
    ordered: list[str] = []
    stack = [folder_id]
    while stack:
        current = stack.pop()
        if current in ordered:
            continue
        ordered.append(current)
        stack.extend(children.get(current, []))
    return ordered


def _archive_folder_delete_summary(db: Session, folder_id: str) -> dict:
    folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    folder_ids = _archive_folder_descendant_ids(db, folder_id)
    doc_count = db.query(Document).filter(Document.folder_id.in_(folder_ids)).count() if folder_ids else 0
    return {
        "folder_id": folder.id,
        "folder_name": folder.name,
        "folder_count": len(folder_ids),
        "subfolder_count": max(0, len(folder_ids) - 1),
        "document_count": doc_count,
    }


@router.get("/api/archive/folders/{folder_id}/delete-summary")
def archive_folder_delete_summary(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _archive_folder_delete_summary(db, folder_id)



@router.delete("/api/archive/folders/{folder_id}", status_code=204)
def delete_archive_folder(
    folder_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    folder_ids = _archive_folder_descendant_ids(db, folder_id)
    if folder_ids:
        db.query(Document).filter(Document.folder_id.in_(folder_ids)).delete(synchronize_session=False)
        for fid in reversed(folder_ids):
            db.query(DocumentFolder).filter(DocumentFolder.id == fid).delete(synchronize_session=False)
    else:
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
    if body.status and body.status not in DOCUMENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status harus salah satu: {', '.join(sorted(DOCUMENT_STATUSES))}")
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        folder_id=body.folder_id or None,
        name=body.title.strip(),
        type="document" if body.body else ("link" if body.url else "document"),
        content=body.body or None,
        title=body.title.strip(),
        body=body.body or None,
        url=body.url or None,
        tags=json.dumps(body.tags or []),
        status=body.status or DocumentStatus.DRAFT,
        created_at=now,
        updated_at=now,
    )
    db.add(doc)
    db.commit()
    return _archive_doc_to_dict(doc)


@router.post("/api/archive/{doc_id}/attachment", status_code=201)
async def upload_archive_attachment(
    doc_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    allowed_ext = {".jpg", ".jpeg", ".png", ".pdf", ".webp", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Format tidak diizinkan: {ext or '-'}")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File terlalu besar (max 10MB)")

    archive_dir = os.path.join(UPLOADS_DIR, "archive", doc_id)
    os.makedirs(archive_dir, exist_ok=True)
    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = os.path.join(archive_dir, fname)
    with open(fpath, "wb") as fh:
        fh.write(contents)

    doc.url = f"/uploads/archive/{doc_id}/{fname}"
    doc.file_size = len(contents)
    doc.type = "file"
    doc.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {**_archive_doc_to_dict(doc), "file_name": file.filename or fname, "file_size": len(contents)}



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
        doc.name = body.title.strip()
    if "body" in changes:
        doc.body = body.body or None
        doc.content = body.body or None
    if "url" in changes:
        doc.url = body.url or None
        doc.type = "link" if body.url else "document"
    if "tags" in changes:
        doc.tags = json.dumps(body.tags or [])
    if "status" in changes:
        if body.status and body.status not in DOCUMENT_STATUSES:
            raise HTTPException(status_code=400, detail=f"Status harus salah satu: {', '.join(sorted(DOCUMENT_STATUSES))}")
        doc.status = body.status or DocumentStatus.DRAFT
    if "review_notes" in changes:
        doc.review_notes = body.review_notes or None
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
    # Normalize legacy URLs: generated documents were stored as bare filenames
    # (e.g. "uuid.pdf") instead of full paths. Rewrite them so the frontend
    # links resolve to the correct API-served file.
    url = doc.url
    if url and not url.startswith(("http://", "https://", "/uploads/")) and url.lower().endswith(".pdf"):
        url = f"/uploads/generated_documents/{url}"
    return {
        "id": doc.id,
        "folder_id": doc.folder_id,
        "title": doc.title,
        "body": doc.body,
        "url": url,
        "tags": tags,
        "status": getattr(doc, "status", DocumentStatus.DRAFT),
        "review_notes": getattr(doc, "review_notes", None),
        "source_type": getattr(doc, "source_type", None),
        "source_id": getattr(doc, "source_id", None),
        "file_size": getattr(doc, "file_size", None),
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


@router.get("/api/documents/health")
def document_health(current_user: User = Depends(get_current_user)):
    """Debug endpoint: surface which PDF renderer + fontconfig path is active.

    Useful when preview shows blank text. Inspect `X-Pdf-Renderer` header
    of any preview/generate response, or hit this endpoint and look at
    `renderer` — if it says `weasyprint` on a host without the fontconfig
    override, the PDF text will be invisible.
    """
    diag = pdf_render_diagnostics()
    diag["renderer"] = diag["pdf_renderer_env"]
    diag["notes"] = (
        "WeasyPrint needs FONTCONFIG_FILE -> Droid Sans Fallback or text will be blank."
    )
    return diag


def _office_profile(profile: str) -> str:
    return "default" if profile == "friday" else profile
