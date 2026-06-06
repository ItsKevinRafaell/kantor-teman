"""Document Service Layer — extracted from routers/documents.py and routers/other.py"""
import json
import uuid
import re
import html as html_mod
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    BrandKit, BrandAsset, DocumentTemplate, GeneratedDocument, DocumentSequence,
    PaymentMethod, Lead, Contact, Project, Document, DocumentFolder,
)
from app.core.dependencies import _get_setting, UPLOADS_DIR

try:
    from document_template_library import get_document_template_starters
except ImportError:
    get_document_template_starters = lambda: {}


DOCUMENTS_DIR = os.path.join(UPLOADS_DIR, "documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

_DOC_TYPE_PREFIX = {
    "invoice": "INV",
    "receipt": "RCPT",
    "proposal_pdf": "PROP",
    "kontrak": "KTR",
    "surat_penawaran": "SP",
    "custom": "DOC",
}

_PDF_FONT_CSS = """
@font-face {
    font-family: 'PDF Sans';
    src: local('DejaVu Sans'), local('Arial'), local('Helvetica'), local('Liberation Sans');
    font-weight: normal;
    font-style: normal;
}
@font-face {
    font-family: 'PDF Sans';
    src: local('DejaVu Sans Bold'), local('Arial Bold'), local('Helvetica Bold'), local('Liberation Sans Bold');
    font-weight: bold;
    font-style: normal;
}
* { font-family: 'PDF Sans', sans-serif !important; }
"""

TRACKING_PIXEL_PNG = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


# ─── Brand Kit ────────────────────────────────────────────────────────────────

def _get_active_kit(db: Session) -> BrandKit:
    kit = db.query(BrandKit).filter(BrandKit.is_active == True).first()
    if not kit:
        kit = db.query(BrandKit).first()
    if not kit:
        raise ValueError("Brand kit tidak ditemukan")
    return kit


def serialize_brand_kit(kit: BrandKit, db: Session) -> dict:
    assets = db.query(BrandAsset).filter(
        BrandAsset.kit_id == kit.id
    ).order_by(BrandAsset.asset_type, BrandAsset.position).all()
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


def build_brand_context(db: Session) -> dict:
    kit = db.query(BrandKit).filter(BrandKit.is_active == True).first() or db.query(BrandKit).first()
    ctx = {
        "logo": "", "colors": {}, "fonts": {}, "tagline": "",
        "nama_perusahaan": "", "brand_name": "", "alamat_perusahaan": "", "phone_perusahaan": "", "email_perusahaan": "",
    }
    if not kit:
        return ctx
    brand_name = getattr(kit, "brand_name", None) or kit.kit_name or ""
    ctx["nama_perusahaan"] = brand_name
    ctx["brand_name"] = brand_name
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


# ─── Template helpers ─────────────────────────────────────────────────────────

def get_document_template_type(template: DocumentTemplate) -> str:
    _BUILTIN_DOCUMENT_TEMPLATE_TYPES = {
        "Invoice": "invoice",
        "Receipt / Bukti Pembayaran": "receipt",
        "Proposal Penawaran PDF": "proposal_pdf",
        "Surat Penawaran Formal": "surat_penawaran",
        "Kontrak / MoU": "kontrak",
    }
    return _BUILTIN_DOCUMENT_TEMPLATE_TYPES.get(
        getattr(template, "name", ""),
        getattr(template, "type", None) or "custom",
    )


def document_template_starter(template_type: str) -> Optional[dict]:
    starters = get_document_template_starters()
    return starters.get(template_type)


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


# ─── Document Sequence (invoice numbering) ────────────────────────────────────

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


def get_invoice_sequence(db: Session, template_type: str = "invoice") -> dict:
    seq = db.query(DocumentSequence).filter(
        DocumentSequence.target_id == "GLOBAL",
        DocumentSequence.template_type == template_type,
    ).first()
    last = seq.last_seq if seq else 0
    return {"template_type": template_type, "last_seq": last, "next_seq": last + 1}


def set_invoice_sequence(db: Session, template_type: str, start_from: int) -> dict:
    seq = db.query(DocumentSequence).filter(
        DocumentSequence.target_id == "GLOBAL",
        DocumentSequence.template_type == template_type,
    ).first()
    if not seq:
        seq = DocumentSequence(target_id="GLOBAL", template_type=template_type, last_seq=0)
        db.add(seq)
    seq.last_seq = start_from - 1
    db.commit()
    return {"template_type": template_type, "last_seq": seq.last_seq, "next_seq": seq.last_seq + 1}


# ─── Document filename builder ─────────────────────────────────────────────────

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


def _generate_document_filename(db: Session, template_type: str, target_type: Optional[str], target_id: Optional[str]) -> str:
    prefix = _DOC_TYPE_PREFIX.get(template_type, "DOC")
    name = _resolve_target_name(db, target_type, target_id)
    slug = _slugify_name(name)
    seq = _next_doc_sequence(db, target_id or "GLOBAL", template_type)
    yyyymm = datetime.now(timezone.utc).strftime("%Y%m")
    return f"{prefix}_{slug}_{seq:03d}_{yyyymm}"


# ─── HTML rendering ────────────────────────────────────────────────────────────

def render_document_html(html_template: str, full_vars: dict) -> str:
    try:
        from jinja2 import Template as JinjaTemplate
        rendered_html = JinjaTemplate(html_template).render(**full_vars)
        for k, v in full_vars.items():
            if isinstance(v, str):
                rendered_html = rendered_html.replace(f"{{{{{k}}}}}", v)
    except ImportError:
        rendered_html = html_template
        for k, v in full_vars.items():
            if isinstance(v, str):
                rendered_html = rendered_html.replace(f"{{{{{k}}}}}", v)
    except Exception as e:
        raise ValueError(f"Render template gagal: {e}")
    return rendered_html


def visible_text_from_html(html: str) -> str:
    without_assets = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_assets)
    return " ".join(html_mod.unescape(without_tags).split())


def inject_pdf_font(html: str) -> str:
    font_tag = f"<style>{_PDF_FONT_CSS}</style>"
    if "<head>" in html:
        return html.replace("<head>", f"<head>{font_tag}", 1)
    if "<html>" in html:
        return html.replace("<html>", f"<html><head>{font_tag}</head>", 1)
    return f"<html><head>{font_tag}</head><body>{html}</body></html>"


def _pdf_escape_text(text: str) -> str:
    text = (
        text.replace("\u00a0", " ")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    text = text.encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def html_to_pdf_lines(rendered_html: str) -> list[str]:
    text_html = re.sub(r"<(style|script)\b[^>]*>.*?</\1>", " ", rendered_html, flags=re.IGNORECASE | re.DOTALL)
    text_html = re.sub(r"<\s*br\s*/?\s*>", "\n", text_html, flags=re.IGNORECASE)
    text_html = re.sub(r"</\s*(p|div|h[1-6]|tr|section|table|thead|tbody|tfoot)\s*>", "\n", text_html, flags=re.IGNORECASE)
    text_html = re.sub(r"</\s*(td|th)\s*>", " | ", text_html, flags=re.IGNORECASE)
    text = html_mod.unescape(re.sub(r"<[^>]+>", " ", text_html))
    raw_lines = [" ".join(line.split()) for line in text.splitlines()]
    lines: list[str] = []
    for line in raw_lines:
        if not line:
            if lines and lines[-1]:
                lines.append("")
            continue
        while len(line) > 96:
            split_at = line.rfind(" ", 0, 96)
            if split_at < 40:
                split_at = 96
            lines.append(line[:split_at].strip())
            line = line[split_at:].strip()
        lines.append(line)
    return lines or ["Dokumen tidak memiliki teks yang dapat ditampilkan."]


def render_text_fallback_pdf(rendered_html: str) -> bytes:
    lines = html_to_pdf_lines(rendered_html)
    page_width = 595
    page_height = 842
    margin_x = 46
    start_y = 792
    lines_per_page = 55
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)] or [[]]

    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    catalog_id = add_object(b"<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object(b"")
    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    page_ids: list[int] = []

    for page_lines in pages:
        content_parts = ["BT", "/F1 10 Tf", f"{margin_x} {start_y} Td", "14 TL"]
        first = True
        for line in page_lines:
            if not first:
                content_parts.append("T*")
            first = False
            if line:
                content_parts.append(f"({_pdf_escape_text(line)}) Tj")
        content_parts.append("ET")
        stream = "\n".join(content_parts).encode("latin-1", "replace")
        content_id = add_object(
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_id = add_object(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


# ─── Template type detection (for PDF rendering) ──────────────────────────────

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
    return _BUILTIN_DOCUMENT_TEMPLATE_TYPES.get(
        getattr(template, "name", ""),
        getattr(template, "type", None) or "custom",
    )


def _document_template_html(template: DocumentTemplate) -> str:
    template_type = _document_template_type(template)
    html_template = template.html_template or ""
    markers = _LEGACY_DOCUMENT_TEMPLATE_MARKERS.get(template_type, ())
    is_legacy = any(marker in html_template for marker in markers)
    template_name = getattr(template, "name", "")
    has_wrong_builtin_type = template_name in _BUILTIN_DOCUMENT_TEMPLATE_TYPES and getattr(template, "type", None) != template_type
    starter = document_template_starter(template_type)
    uses_deprecated_company_scope = (
        template_name in _BUILTIN_DOCUMENT_TEMPLATE_TYPES
        and starter
        and "{{brand_name}}" not in html_template
        and "{{nama_perusahaan}}" in html_template
    )
    if (is_legacy or has_wrong_builtin_type or uses_deprecated_company_scope) and starter:
        return starter["html_template"]
    return html_template


# ─── Default variables builder ───────────────────────────────────────────────

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


def _build_default_vars(db: Session, template_type: str, target_type: Optional[str], target_id: Optional[str]) -> dict:
    today = datetime.now(timezone.utc)
    brand = build_brand_context(db)

    defaults: dict = {
        "tanggal": _format_date_id(today),
        "logo": brand.get("logo", ""),
        "brand_name": brand.get("brand_name", ""),
        "tagline": brand.get("tagline", ""),
    }

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

    service_name = ""
    if lead:
        service_name = lead.product_interest or ""
    elif contact:
        service_name = contact.purchased_product or ""

    if template_type == "invoice":
        seq = _peek_doc_sequence(db, "GLOBAL", "invoice")
        yyyymm = today.strftime("%Y%m")
        defaults["nomor_invoice"] = f"INV/{yyyymm}/{seq:03d}"
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
        seq = _peek_doc_sequence(db, "GLOBAL", "receipt")
        yyyymm = today.strftime("%Y%m")
        defaults["nomor"] = f"RCPT/{yyyymm}/{seq:03d}"
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
            from calendar import monthrange
            end_month = (today.month - 1 + durasi_months) % 12 + 1
            end_year = today.year + (today.month - 1 + durasi_months) // 12
            end_day = min(today.day, monthrange(end_year, end_month)[1])
            defaults["tanggal_akhir"] = _format_date_id(today.replace(year=end_year, month=end_month, day=end_day))

    elif template_type == "surat_penawaran":
        seq = _peek_doc_sequence(db, "GLOBAL", "surat_penawaran")
        yyyymm = today.strftime("%Y%m")
        defaults["nomor"] = f"SP/{yyyymm}/{seq:03d}"
        defaults["perihal"] = f"Penawaran Jasa {service_name}".strip()
        defaults["terms"] = "Penawaran ini berlaku 14 hari sejak tanggal surat. Harga belum termasuk pajak kecuali disebutkan lain."

    return defaults


# ─── Document PDF generation ──────────────────────────────────────────────────

def _render_document_pdf_bytes(template: DocumentTemplate, full_vars: dict) -> bytes:
    """Render template to PDF bytes using WeasyPrint."""
    template_type = _document_template_type(template)
    rendered_html = render_document_html(_document_template_html(template), full_vars)
    if not visible_text_from_html(rendered_html):
        starter = document_template_starter(template_type)
        if starter:
            rendered_html = render_document_html(starter["html_template"], full_vars)
    if not visible_text_from_html(rendered_html):
        raise ValueError("Template PDF kosong. Isi HTML template terlebih dahulu.")

    rendered_html = inject_pdf_font(rendered_html)

    def _pdf_url_fetcher(url: str, **kw):
        return {"string": b"", "mime_type": "text/plain"}

    try:
        from weasyprint import HTML
        pdf = HTML(string=rendered_html, url_fetcher=_pdf_url_fetcher).write_pdf()
        if not pdf or not pdf.startswith(b"%PDF") or len(pdf) < 1024:
            raise ValueError("PDF generation menghasilkan halaman kosong")
        if (
            os.getenv("PDF_FORCE_TEXT_FALLBACK", "").lower() == "true"
            or len(pdf) < int(os.getenv("PDF_BLANK_FALLBACK_MAX_BYTES", "8192"))
        ):
            return render_text_fallback_pdf(rendered_html)
        return pdf
    except ImportError:
        raise ValueError("WeasyPrint tidak terinstall. Jalankan: pip install weasyprint")
    except Exception as e:
        raise ValueError(f"PDF generation gagal: {e}")


def generate_document_pdf(
    db: Session,
    template_id: str,
    target_type: Optional[str],
    target_id: Optional[str],
    variables: dict,
    actor: str,
    documents_dir: str = DOCUMENTS_DIR,
) -> dict:
    """Full document generation pipeline. Creates GeneratedDocument record."""
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not template:
        raise ValueError("Template tidak ditemukan")

    template_type = get_document_template_type(template)
    defaults = _build_default_vars(db, template_type, target_type, target_id)
    brand_ctx = build_brand_context(db)
    full_vars = {**brand_ctx, **defaults}
    for key, value in variables.items():
        value = _normalize_document_variable(key, value)
        if key in _SERVER_OWNED_DOCUMENT_KEYS and full_vars.get(key) not in (None, ""):
            continue
        if value not in (None, "") or key not in full_vars:
            full_vars[key] = value
    for key, value in list(full_vars.items()):
        full_vars[key] = _normalize_document_variable(key, value)
    if "logo" not in variables:
        full_vars["logo"] = brand_ctx["logo"]

    # Reserve and apply document number
    number = None
    if template_type in ("invoice", "receipt", "surat_penawaran"):
        number = _document_number(db, template_type, reserve=True)
        if template_type == "invoice":
            full_vars["nomor_invoice"] = number
            full_vars["no_invoice"] = number
        else:
            full_vars["nomor"] = number

    # Render PDF
    pdf_bytes = _render_document_pdf_bytes(template, full_vars)

    # Save to disk
    file_id = str(uuid.uuid4())
    pdf_filename = f"{file_id}.pdf"
    pdf_path = os.path.join(documents_dir, pdf_filename)
    with open(pdf_path, "wb") as pdf_file:
        pdf_file.write(pdf_bytes)

    # Build display name
    client_name = full_vars.get("klien") or full_vars.get("nama") or ""
    invoice_no = full_vars.get("nomor_invoice") or full_vars.get("no_invoice") or full_vars.get("nomor") or ""
    prefix = _DOC_TYPE_PREFIX.get(template_type, "DOC")
    client_slug = _slugify_name(client_name) if client_name else "Dokumen"
    if invoice_no:
        inv_slug = invoice_no.replace("/", "-").replace(" ", "-")
        display_name = f"{prefix}_{client_slug}_{inv_slug}"
    else:
        display_name = _generate_document_filename(db, template_type, target_type, target_id)

    file_url = f"/uploads/documents/{pdf_filename}"
    doc = GeneratedDocument(
        id=file_id,
        template_id=template.id,
        template_name=template.name,
        target_type=target_type,
        target_id=target_id,
        variables_used=json.dumps(full_vars),
        file_url=file_url,
        display_filename=display_name,
        generated_by=actor,
    )
    db.add(doc)
    db.commit()

    return {
        "document_id": doc.id,
        "file_url": file_url,
        "template_name": template.name,
        "display_filename": display_name,
    }


def _document_number(db: Session, template_type: str, reserve: bool = False) -> str:
    prefixes = {"invoice": "INV", "receipt": "RCPT", "surat_penawaran": "SP"}
    prefix = prefixes.get(template_type)
    if not prefix:
        return ""
    seq = _next_doc_sequence(db, "GLOBAL", template_type) if reserve else _peek_doc_sequence(db, "GLOBAL", template_type)
    yyyymm = datetime.now(timezone.utc).strftime("%Y%m")
    return f"{prefix}/{yyyymm}/{seq:03d}"


def _apply_final_document_number(db: Session, template_type: str, full_vars: dict) -> None:
    number = _document_number(db, template_type, reserve=True)
    if not number:
        return
    if template_type == "invoice":
        full_vars["nomor_invoice"] = number
        full_vars["no_invoice"] = number
    else:
        full_vars["nomor"] = number


# ─── Template CRUD ────────────────────────────────────────────────────────────

def list_templates(db: Session, product_category: Optional[str] = None) -> list[DocumentTemplate]:
    q = db.query(DocumentTemplate).filter(DocumentTemplate.is_active == True)
    return q.order_by(DocumentTemplate.name).all()


def create_document_template(
    db: Session,
    name: str,
    type: str,
    html_template: str,
    variables: Optional[list],
    is_active: bool = True,
) -> DocumentTemplate:
    valid_types = {"proposal_pdf", "invoice", "receipt", "kontrak", "surat_penawaran", "custom"}
    if type not in valid_types:
        raise ValueError(f"Type harus salah satu: {', '.join(valid_types)}")
    t = DocumentTemplate(
        id=str(uuid.uuid4()),
        name=name,
        type=type,
        html_template=html_template,
        variables=json.dumps(variables or []),
        is_active=is_active,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def update_document_template(db: Session, template_id: str, updates: dict) -> DocumentTemplate:
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise ValueError("Template tidak ditemukan")
    for key in ("name", "type", "html_template", "is_active"):
        if key in updates:
            setattr(t, key, updates[key])
    if "variables" in updates:
        t.variables = json.dumps(updates["variables"])
    db.commit()
    db.refresh(t)
    return t


def delete_document_template(db: Session, template_id: str) -> None:
    t = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not t:
        raise ValueError("Template tidak ditemukan")
    db.delete(t)
    db.commit()
