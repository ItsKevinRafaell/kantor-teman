"""Sales workflow orchestration: deal acceptance, archive, billing, documents."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.constants import DocumentStatus, PaymentStatus
from app.services.document_service import generate_document_pdf
from app.services.notification_service import create_notification
from models import (
    Board, BoardCard, BoardColumn, Contact, Document, DocumentFolder,
    DocumentTemplate, GeneratedDocument, Lead, Project, Proposal, SystemSettings,
    WorkspaceCell, WorkspaceColumn, WorkspaceRow, WorkspaceSheet,
)
from models.base import log_audit
from app.core.dependencies import (
    ADMIN_WA,
    WORKSPACE_TEMPLATES,
    _get_setting,
    _send_fonnte_sync,
    build_sheets_for_service,
    get_fonnte_token,
    sync_row_to_board,
    _detect_service_types,
    normalize_service_type,
)
from app.services.proposal_service import (
    detect_contract_months,
    detect_project_type,
    detect_service_type,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_admin_user_id(db: Session) -> Optional[int]:
    from models import User
    user = db.query(User).filter(User.role == "admin").order_by(User.id.asc()).first()
    if not user:
        user = db.query(User).order_by(User.id.asc()).first()
    return user.id if user else None


def get_default_dp_percent(db: Session) -> float:
    row = db.query(SystemSettings).filter(SystemSettings.key == "default_dp_percent").first()
    value = row.value if row and row.value else "50"
    try:
        percent = float(value)
    except Exception:
        percent = 50.0
    return min(100.0, max(0.0, percent))


def set_default_dp_percent(db: Session, percent: float) -> float:
    pct = min(100.0, max(0.0, float(percent)))
    row = db.query(SystemSettings).filter(SystemSettings.key == "default_dp_percent").first()
    if not row:
        db.add(SystemSettings(key="default_dp_percent", value=str(pct)))
    else:
        row.value = str(pct)
    db.commit()
    return pct


def _format_idr(amount: float) -> str:
    return f"Rp {amount:,.0f}".replace(",", ".")


def _items_rows(items: list[dict]) -> str:
    if not items:
        return '<table class="w100"><tr><td class="muted">Tidak ada item</td></tr></table>'
    rows = [
        '<table class="w100" cellspacing="0" cellpadding="6" style="border:1pt solid #d1d5db">',
        '<tr><th align="left">Layanan</th><th align="right">Nilai</th></tr>',
    ]
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{item.get('name', '-')}</td>"
            f"<td align=\"right\">{_format_idr(float(item.get('price') or 0))}</td>"
            "</tr>"
        )
    total = sum(float(item.get("price") or 0) for item in items)
    rows.append(f'<tr><td><b>Total</b></td><td align="right"><b>{_format_idr(total)}</b></td></tr>')
    rows.append("</table>")
    return "".join(rows)


def _get_or_create_folder(db: Session, user_id: int, name: str, parent_id: Optional[str], color: str = "#6B7280") -> DocumentFolder:
    folder = db.query(DocumentFolder).filter(
        DocumentFolder.user_id == user_id,
        DocumentFolder.name == name,
        DocumentFolder.parent_id == parent_id,
    ).first()
    if folder:
        return folder
    folder = DocumentFolder(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        parent_id=parent_id,
        color=color,
        created_at=_now(),
    )
    db.add(folder)
    db.flush()
    return folder


def ensure_archive_folder_tree(
    db: Session,
    client_name: str,
    project_name: str,
    doc_type: str,
    user_id: Optional[int] = None,
) -> Optional[DocumentFolder]:
    """Return a flat top-level folder based on document type only.

    Previously generated a deep 3-level tree (Client -> Project -> Type).
    Now archives go directly into root-level folders like Invoice, Kontrak,
    Proposal, etc. so the structure is shallow and easier for drag-and-drop.
    """
    uid = user_id or _first_admin_user_id(db)
    if not uid:
        return None
    return _get_or_create_folder(db, uid, doc_type, None, "#6B7280")


def archive_generated_document(
    db: Session,
    generated_doc: GeneratedDocument,
    title: str,
    client_name: str,
    project_name: str,
    doc_type: str,
    folder_id: Optional[str] = None,
    lead_id: Optional[int] = None,
) -> Optional[Document]:
    """Copy generated PDF into Arsip Tim.

    folder_id: if set, use that folder (must exist). Else auto-create client/project tree.
    lead_id: optional CRM link for hub.
    """
    user_id = _first_admin_user_id(db)
    if not user_id:
        return None
    folder = None
    if folder_id:
        folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first()
        if not folder:
            return None
    else:
        folder = ensure_archive_folder_tree(db, client_name, project_name, doc_type)
    if not folder:
        return None
    existing = db.query(Document).filter(Document.source_type == "generated_document", Document.source_id == generated_doc.id).first()
    if existing:
        if folder_id and existing.folder_id != folder.id:
            existing.folder_id = folder.id
            existing.updated_at = _now()
        if lead_id is not None and getattr(existing, "lead_id", None) != lead_id:
            existing.lead_id = lead_id
            existing.updated_at = _now()
        return existing
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=user_id,
        folder_id=folder.id,
        lead_id=lead_id,
        name=title,
        type="pdf",
        content=None,
        title=title,
        body=None,
        url=generated_doc.file_url,
        tags=json.dumps([doc_type, generated_doc.status or DocumentStatus.DRAFT]),
        status=generated_doc.status or DocumentStatus.DRAFT,
        source_type="generated_document",
        source_id=generated_doc.id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(doc)
    return doc


def _find_template(db: Session, template_type: str) -> Optional[DocumentTemplate]:
    return db.query(DocumentTemplate).filter(
        DocumentTemplate.type == template_type,
        DocumentTemplate.is_active == True,
    ).order_by(DocumentTemplate.created_at.desc()).first()


def _generate_workflow_document(
    db: Session,
    template_type: str,
    target_type: str,
    target_id: str,
    variables: dict,
    actor: str,
    status: str,
    payment_status: Optional[str],
    archive_title: str,
    client_name: str,
    project_name: str,
    doc_type_label: str,
) -> tuple[Optional[GeneratedDocument], Optional[str]]:
    """Generate satu dokumen workflow secara terisolasi.

    Return (doc, failure_reason):
      - (doc, None)         -> sukses
      - (None, "missing_template:<type>") -> template tidak ada
      - (None, "<pesan error>")           -> generate gagal

    PENTING (fix P0-2): tiap generate dibungkus SAVEPOINT (db.begin_nested()),
    JANGAN db.rollback() global. Kalau 1 dokumen gagal, cuma savepoint dokumen
    itu yang dibatalkan — dokumen lain + invoice DP + notif yang sudah dibuat di
    sesi yang sama TETAP aman (tidak ikut lenyap diam-diam).
    """
    template = _find_template(db, template_type)
    if not template:
        return None, f"missing_template:{template_type}"
    try:
        with db.begin_nested():  # SAVEPOINT: isolasi kegagalan per-dokumen
            result = generate_document_pdf(
                db=db,
                template_id=template.id,
                target_type=target_type,
                target_id=target_id,
                variables=variables,
                actor=actor,
            )
            doc = db.query(GeneratedDocument).filter(
                GeneratedDocument.id == result["document_id"]
            ).first()
            if not doc:
                # rollback savepoint via raise -> tidak ada residu
                raise RuntimeError("generated document row tidak ditemukan setelah generate")
            doc.status = status
            doc.payment_status = payment_status
            try:
                archive_generated_document(
                    db, doc, archive_title, client_name, project_name, doc_type_label
                )
            except Exception as e:
                # Arsip gagal tidak boleh membatalkan dokumen inti — cukup catat.
                print(f"[WORKFLOW_ARCHIVE] skip {doc.id}: {e}", flush=True)
            db.flush()
    except Exception as e:
        # Hanya savepoint yang di-rollback; sesi utama tetap utuh.
        print(f"[WORKFLOW_DOCUMENT] gagal {template_type}: {e}", flush=True)
        return None, str(e)
    return doc, None


def ensure_contact_for_lead(db: Session, lead: Lead, owner_name: Optional[str] = None, phone: Optional[str] = None) -> Contact:
    contact = db.query(Contact).filter(Contact.phone_number == (phone or lead.phone_number)).first()
    if contact:
        if not contact.lead_id:
            contact.lead_id = lead.id
        if owner_name and not contact.owner_name:
            contact.owner_name = owner_name
        return contact
    contact = Contact(
        business_name=lead.business_name,
        owner_name=owner_name,
        phone_number=phone or lead.phone_number,
        purchased_product=lead.product_interest,
        lead_id=lead.id,
    )
    db.add(contact)
    db.flush()
    return contact


def create_project_board_workspace(
    db: Session,
    proposal: Proposal,
    lead: Lead,
    client_name: str,
) -> Project:
    services = json.loads(proposal.services_detail) if proposal.services_detail else []
    project_type = detect_project_type(services)
    service_type = detect_service_type(services)
    service_types_all = _detect_service_types(services)
    service_type_combined = ",".join(service_types_all) if service_types_all else service_type
    months = detect_contract_months(proposal, services, _now()[:10], None)
    active_price = proposal.discount_price or proposal.total_price
    service_names = ", ".join(s.get("name", "") for s in services[:2])
    project_name = f"{service_names} - {lead.business_name}" if service_names else f"Project {lead.business_name}"

    project = Project(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        proposal_id=proposal.id,
        name=project_name,
        type=project_type,
        status="ACTIVE",
        nominal=active_price,
        start_date=_now()[:10],
        color="gray",
        service_type=service_type_combined,
        contract_months=months,
        dp_percent=get_default_dp_percent(db),
        monthly_invoice_enabled=(project_type == "RETAINER"),
        next_invoice_date=(datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat() if project_type == "RETAINER" else None,
    )
    db.add(project)
    db.flush()

    board = Board(id=str(uuid.uuid4()), project_id=project.id)
    db.add(board)
    db.flush()

    todo_col_id = None
    for i, (name, color) in enumerate([("To Do", "gray"), ("In Progress", "slate"), ("Review", "neutral"), ("Done", "stone")]):
        col = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=name, position=i, color=color)
        db.add(col)
        if name == "To Do":
            todo_col_id = col.id

    base_cards = [
        "Kick-off call dengan klien",
        "Kumpulkan brief dan akses",
        "Approval timeline dan milestone",
        "Kirim deliverable pertama",
    ]
    service_cards = {
        "web_dev": ["Setup domain/hosting", "Wireframe approval", "Development sprint pertama"],
        "web_dev_bulanan": ["Setup backlog bulanan", "Sprint planning", "Laporan progres pertama"],
        "seo_gmaps": ["Audit website/GBP awal", "Riset keyword lokal", "On-page optimization"],
        "sosmed": ["Content calendar approval", "Desain template feed", "Posting perdana"],
        "maintenance": ["Inventarisasi aset klien", "Setup monitoring", "Laporan kondisi awal"],
        "branding": ["Brief visual", "Moodboard approval", "Konsep awal"],
    }
    if todo_col_id:
        now_cards = _now()
        for pos, title in enumerate(base_cards + service_cards.get(service_type or "", [])):
            db.add(BoardCard(
                id=str(uuid.uuid4()),
                column_id=todo_col_id,
                title=title,
                labels=json.dumps(["onboarding"]),
                position=pos,
                updated_at=now_cards,
            ))

    # Normalisasi service_type: bisa None (detect gagal) atau gabungan
    # ("seo_gmaps,maintenance"). Pakai combined dulu supaya klien SEO tetap dapat
    # template seo_gmaps, baru fallback ke single detect, terakhir "general".
    workspace_type = normalize_service_type(service_type_combined or service_type)
    sheet_defs = build_sheets_for_service(workspace_type, months)
    now_ws = _now()
    for idx, sdef in enumerate(sheet_defs):
        sheet = WorkspaceSheet(
            id=str(uuid.uuid4()),
            project_id=project.id,
            sheet_index=idx,
            sheet_label=sdef["label"],
            service_type=workspace_type,
            month_number=sdef.get("month"),
            created_at=now_ws,
        )
        db.add(sheet)
        db.flush()
        col_map = {}
        for ci, cdef in enumerate(sdef["columns"]):
            col = WorkspaceColumn(
                id=str(uuid.uuid4()),
                sheet_id=sheet.id,
                column_key=cdef["key"],
                column_label=cdef["label"],
                column_type=cdef["type"],
                column_options=json.dumps(cdef.get("options", [])),
                column_order=ci,
                is_system=cdef.get("is_system", False),
                created_at=now_ws,
            )
            db.add(col)
            db.flush()
            col_map[cdef["key"]] = col
        for ri, rdef in enumerate(sdef.get("default_rows", [])):
            row = WorkspaceRow(id=str(uuid.uuid4()), sheet_id=sheet.id, row_order=ri, is_template=True, created_at=now_ws)
            db.add(row)
            db.flush()
            for key, val in rdef.items():
                col = col_map.get(key)
                if not col:
                    continue
                cell = WorkspaceCell(id=str(uuid.uuid4()), row_id=row.id, column_id=col.id, updated_at=now_ws)
                if col.column_type == "checkbox":
                    cell.value_bool = bool(val)
                elif col.column_type == "number":
                    cell.value_number = float(val) if val else None
                else:
                    cell.value_text = str(val) if val else None
                db.add(cell)
            db.flush()
            sync_row_to_board(row.id, db)

    return project


def generate_acceptance_documents(
    db: Session,
    proposal: Proposal,
    project: Project,
    lead: Lead,
    actor: str = "system",
) -> list[GeneratedDocument]:
    services = json.loads(proposal.services_detail) if proposal.services_detail else []
    client_name = lead.business_name
    active_price = proposal.discount_price or proposal.total_price
    dp_percent = project.dp_percent if project.dp_percent is not None else get_default_dp_percent(db)
    dp_amount = round((active_price or 0) * dp_percent / 100)
    service_label = ", ".join(s.get("name", "") for s in services if s.get("name")) or project.name
    generated: list[GeneratedDocument] = []

    common = {
        "klien": client_name,
        "nama": client_name,
        "alamat": lead.address or "",
        "phone": lead.phone_number or "",
        "layanan": service_label,
        "scope": "\n".join(f"- {s.get('name', '')}" for s in services if s.get("name")),
        "items_rows": _items_rows(services),
    }

    failed: list[dict] = []  # {doc: label, reason: str}

    def _record_failure(label: str, reason: str) -> None:
        failed.append({"doc": label, "reason": reason})
        try:
            log_audit(
                db, actor, "workflow_document_failed", "projects", project.id,
                {"document": label, "reason": reason, "proposal_id": proposal.id},
                commit=False,  # JANGAN commit di tengah flow accept (savepoint-safe)
            )
        except Exception as e:
            print(f"[WORKFLOW_AUDIT] gagal catat {label}: {e}", flush=True)

    # ── Invoice DP DULUAN & WAJIB ────────────────────────────────────────────
    # Titik-uang paling penting. Kalau gagal -> seluruh accept dianggap gagal
    # (raise), jangan lanjut seolah sukses (fix P0-2).
    invoice, invoice_err = _generate_workflow_document(
        db, "invoice", "project", project.id,
        {
            **common,
            "items_rows": _items_rows([{"name": f"Invoice DP {dp_percent:.0f}% - {service_label}", "price": dp_amount}]),
            "catatan": f"Invoice DP {dp_percent:.0f}% dari nilai project {_format_idr(active_price or 0)}.",
            "terms": "Invoice DP dibayarkan sebelum pekerjaan utama dimulai.",
        },
        actor, DocumentStatus.DRAFT, PaymentStatus.UNPAID,
        f"Invoice DP {dp_percent:.0f}%", client_name, project.name, "Invoice",
    )
    if invoice:
        generated.append(invoice)
    else:
        _record_failure("Invoice DP", invoice_err or "unknown")
        raise ValueError(
            f"Gagal membuat invoice DP (dokumen wajib): {invoice_err}. "
            "Accept dibatalkan supaya tidak ada project tanpa invoice."
        )

    proposal_pdf, err = _generate_workflow_document(
        db, "proposal_pdf", "project", project.id,
        {**common, "catatan": "Proposal penawaran yang sudah diterima dan disimpan sebagai arsip."},
        actor, DocumentStatus.SENT, None,
        "Proposal Penawaran", client_name, project.name, "Proposal",
    )
    if proposal_pdf:
        generated.append(proposal_pdf)
    elif err:
        _record_failure("Proposal Penawaran", err)

    mou, err = _generate_workflow_document(
        db, "mou", "project", project.id,
        {**common, "tujuan": "Menetapkan dasar kerja sama awal setelah proposal disetujui."},
        actor, DocumentStatus.DRAFT, None,
        "Draft MOU", client_name, project.name, "MOU",
    )
    if mou:
        generated.append(mou)
    elif err:
        _record_failure("Draft MOU", err)

    # Pick service-specific contract template(s) based on project.service_type
    # service_type can be comma-separated (e.g. "maintenance,seo_gmaps")
    service_type_raw = getattr(project, "service_type", None) or ""
    service_types = (
        [s.strip() for s in service_type_raw.split(",") if s.strip()]
        if "," in service_type_raw else [service_type_raw]
    )

    kontrak_type_map = {
        "web_dev": "kontrak_web_dev",
        "web_dev_bulanan": "kontrak_web_dev",
        "seo_gmaps": "kontrak_seo",
        "sosmed": "kontrak_sosmed",
        "maintenance": "kontrak_maintenance",
        "branding": "kontrak_branding",
        "RETAINER": "kontrak_retainer",
    }
    kontrak_label_map = {
        "kontrak_web_dev": "Draft Kontrak — Website Development",
        "kontrak_seo": "Draft Kontrak — SEO &amp; Google Business",
        "kontrak_sosmed": "Draft Kontrak — Social Media Management",
        "kontrak_maintenance": "Draft Kontrak — Maintenance &amp; Support",
        "kontrak_branding": "Draft Kontrak — Branding &amp; Visual Identity",
        "kontrak_retainer": "Draft Kontrak — Paket Retainer Bulanan",
    }

    # Import service descriptions for professional wording
    try:
        from document_template_library import get_service_description
    except ImportError:
        def get_service_description(st):
            return {}

    if not service_types:
        service_types = ["kontrak"]

    for stype in service_types:
        kontrak_type = kontrak_type_map.get(stype, "kontrak")
        kontrak_label = kontrak_label_map.get(kontrak_type, "Draft Kontrak")

        # Get professional description for this service type
        svc_desc = get_service_description(stype)

        # Start with common vars + service-specific layanan name
        kontrak_vars = {
            **common,
            "nilai_kontrak": _format_idr(active_price or 0),
            "layanan": svc_desc.get("layanan", service_label),
        }

        # Override defaults with professional descriptions
        desc_keys = [
            "scope", "deliverables", "terms", "out_of_scope", "revision_limit",
            "payment_schedule", "bug_warranty", "ip_rights", "domain_hosting",
            "milestones", "target_keywords", "success_metrics", "disclaimer",
            "reporting", "scope_change", "platforms", "approval_flow",
            "content_ownership", "platform_rules", "escalation",
            "scope_included", "sla_metrics", "coverage_hours",
            "emergency_escalation", "ticket_resolution", "concept_count",
            "moodboard_approval", "color_standards", "file_usage_rights",
            "scope_monthly", "hour_allocation", "addon_rate",
            "change_request_process", "termination_notice",
        ]
        for dk in desc_keys:
            if dk in svc_desc:
                kontrak_vars[dk] = svc_desc[dk]

        # Fallbacks
        if "out_of_scope" not in kontrak_vars:
            kontrak_vars["out_of_scope"] = (
                "Pengembangan fitur baru dan perubahan di luar lingkup "
                "memerlukan addendum terpisah."
            )
        if "payment_schedule" not in kontrak_vars:
            kontrak_vars["payment_schedule"] = (
                f"DP {dp_percent:.0f}% saat penandatanganan kontrak. "
                f"Pelunasan saat serah terima."
            )

        kontrak, err = _generate_workflow_document(
            db, kontrak_type, "project", project.id,
            kontrak_vars,
            actor, DocumentStatus.DRAFT, None,
            kontrak_label, client_name, project.name, "Kontrak",
        )
        if kontrak:
            generated.append(kontrak)
        elif err:
            _record_failure(kontrak_label, err)

    # Kalau ada dokumen non-wajib yang gagal: JANGAN telan diam. Catat + notif
    # supaya admin bisa RE-GENERATE (revisi yang ada, bukan biarin bolong).
    if failed:
        labels = ", ".join(f["doc"] for f in failed)
        create_notification(
            db,
            title="Sebagian dokumen gagal dibuat",
            message=(
                f"Project {project.name}: {len(failed)} dokumen gagal digenerate "
                f"({labels}). Invoice DP aman. Silakan re-generate dokumen yang gagal."
            ),
            notif_type="warning",
            target_type="project",
            target_id=project.id,
            action_url=f"/workspace?project={project.id}",
        )

    return generated


def archive_proposal_pdf_for_lead(
    db: Session,
    proposal: Proposal,
    lead: Lead,
    actor: str = "system",
) -> Optional[GeneratedDocument]:
    services = json.loads(proposal.services_detail) if proposal.services_detail else []
    service_label = ", ".join(s.get("name", "") for s in services if s.get("name")) or lead.product_interest or "Layanan"
    doc, _err = _generate_workflow_document(
        db,
        "proposal_pdf",
        "lead",
        str(lead.id),
        {
            "klien": lead.business_name,
            "nama": lead.business_name,
            "alamat": lead.address or "",
            "phone": lead.phone_number or "",
            "layanan": service_label,
            "scope": "\n".join(f"- {s.get('name', '')}" for s in services if s.get("name")),
            "items_rows": _items_rows(services),
            "catatan": "Proposal penawaran awal sebelum deal.",
        },
        actor,
        DocumentStatus.SENT,
        None,
        "Proposal Penawaran",
        lead.business_name,
        "Pra-Deal",
        "Proposal",
    )
    return doc


def accept_proposal_workflow(
    db: Session,
    proposal: Proposal,
    client_name: str,
    client_phone: str,
    accept_notes: Optional[str],
) -> dict:
    import httpx as _httpx
    from sqlalchemy.exc import IntegrityError

    # ── P0-1: Anti double-accept (idempotent + row lock) ─────────────────────
    # Re-baca proposal dengan ROW LOCK (SELECT ... FOR UPDATE). Di MySQL/InnoDB
    # ini bikin request kedua NUNGGU request pertama commit, lalu baca status
    # terbaru -> ketemu "accepted" -> balikin project yang SUDAH ada (bukan
    # bikin baru). SQLite tak punya row lock, jadi pengaman utama lintas-DB =
    # cek project existing by proposal_id + UNIQUE constraint di kolom itu.
    locked = (
        db.query(Proposal)
        .filter(Proposal.id == proposal.id)
        .with_for_update()
        .first()
    )
    proposal = locked or proposal

    def _existing_project():
        return db.query(Project).filter(Project.proposal_id == proposal.id).first()

    if proposal.status == "accepted":
        project = _existing_project() or (
            db.query(Project)
            .filter(Project.lead_id == proposal.lead_id)
            .order_by(Project.id.desc())
            .first()
        )
        return {"success": True, "project_id": project.id if project else None, "already_accepted": True}
    if proposal.status == "rejected":
        raise ValueError("Proposal sudah ditolak")

    # Pengaman kedua: kalau (karena race) project untuk proposal ini SUDAH ada,
    # jangan bikin baru — pakai yang itu (idempotent).
    already = _existing_project()
    if already:
        if proposal.status != "accepted":
            proposal.status = "accepted"
            proposal.accepted_at = _now()
            db.commit()
        return {"success": True, "project_id": already.id, "already_accepted": True}

    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise ValueError("Lead tidak ditemukan")

    now = _now()
    proposal.status = "accepted"
    proposal.accepted_at = now
    lead.status = "Closed/Client"
    ensure_contact_for_lead(db, lead, owner_name=client_name, phone=client_phone or lead.phone_number)
    try:
        project = create_project_board_workspace(db, proposal, lead, client_name)
        db.commit()
    except IntegrityError:
        # UNIQUE(proposal_id) menolak -> request lain sudah membuat project lebih
        # dulu. Rollback lalu balikin project yang sudah ada (idempotent).
        db.rollback()
        existing = _existing_project()
        if existing:
            return {"success": True, "project_id": existing.id, "already_accepted": True}
        raise
    generated_docs = generate_acceptance_documents(db, proposal, project, lead)

    create_notification(
        db,
        title="Proposal diterima",
        message=f"{lead.business_name} menerima proposal. Project, board, workspace, invoice DP, dan draft dokumen sudah disiapkan.",
        notif_type="deal",
        target_type="project",
        target_id=project.id,
        action_url=f"/workspace?project={project.id}",
    )

    db.commit()

    services = json.loads(proposal.services_detail) if proposal.services_detail else []
    service_names = ", ".join(s.get("name", "") for s in services[:2]) or "-"
    fonnte_token = get_fonnte_token(db)
    admin_wa = _get_setting("admin_wa", ADMIN_WA)
    msg = (
        f"*Proposal Diterima!*\n\n"
        f"Klien: *{lead.business_name}*\n"
        f"Nama: {client_name}\n"
        f"WA: {client_phone or lead.phone_number}\n"
        f"Layanan: {service_names}\n"
        f"Nilai: {_format_idr(proposal.discount_price or proposal.total_price)}\n"
        f"Project ID: {project.id[:8]}...\n\n"
        f"Sistem sudah membuat project, board, workspace, invoice DP, draft MOU/kontrak, arsip dokumen, dan notifikasi web."
    )
    if accept_notes:
        msg += f"\n\nCatatan klien: {accept_notes}"
    threading.Thread(target=_send_fonnte_sync, args=(admin_wa, msg, fonnte_token, _httpx), daemon=True).start()

    return {
        "success": True,
        "project_id": project.id,
        "already_accepted": False,
        "generated_documents": [doc.id for doc in generated_docs],
    }


def get_unpaid_project_invoices(db: Session, project_id: str) -> list[GeneratedDocument]:
    docs = db.query(GeneratedDocument).filter(
        GeneratedDocument.target_type == "project",
        GeneratedDocument.target_id == project_id,
    ).all()
    return [
        doc for doc in docs
        if (doc.template_name or "").lower().find("invoice") >= 0
        and (doc.payment_status or PaymentStatus.UNPAID) != PaymentStatus.PAID
    ]


def assert_project_can_complete(db: Session, project_id: str) -> None:
    unpaid = get_unpaid_project_invoices(db, project_id)
    if unpaid:
        raise ValueError(f"Masih ada {len(unpaid)} invoice yang belum lunas.")


def generate_due_monthly_invoices(db: Session, actor: str = "system") -> list[GeneratedDocument]:
    today = datetime.now(timezone.utc).date()
    projects = db.query(Project).filter(
        Project.status == "ACTIVE",
        Project.monthly_invoice_enabled == True,
        Project.next_invoice_date.isnot(None),
    ).all()
    generated: list[GeneratedDocument] = []
    for project in projects:
        try:
            due = datetime.fromisoformat(project.next_invoice_date[:10]).date()
        except Exception:
            continue
        if due > today:
            continue
        lead = db.query(Lead).filter(Lead.id == project.lead_id).first() if project.lead_id else None
        if not lead:
            continue

        # ── Guard idempotensi periode (fix P0-3) ─────────────────────────────
        # Pertahanan utama: next_invoice_date maju +30 hari tiap dibuat, + cek
        # due>today di atas -> run ganda back-to-back otomatis ke-skip.
        # Pertahanan tambahan (defense-in-depth): kalau arsip invoice bulanan
        # untuk periode (YYYY-MM) ini SUDAH ada, JANGAN bikin baru — cukup
        # majukan tanggal. Lindungi dari retry/crash sebelum next_invoice_date
        # sempat maju.
        period_tag = due.strftime("%Y-%m")
        existing = db.query(GeneratedDocument).filter(
            GeneratedDocument.target_type == "project",
            GeneratedDocument.target_id == project.id,
            GeneratedDocument.template_name == f"Invoice Bulanan {period_tag}",
        ).first()
        if existing:
            next_month = due + timedelta(days=30)
            project.next_invoice_date = next_month.isoformat()
            continue

        doc, _err = _generate_workflow_document(
            db,
            "invoice",
            "project",
            project.id,
            {
                "klien": lead.business_name,
                "nama": lead.business_name,
                "alamat": lead.address or "",
                "phone": lead.phone_number or "",
                "layanan": project.name,
                "items_rows": _items_rows([{"name": f"Invoice bulanan - {project.name}", "price": project.nominal or 0}]),
                "catatan": "Invoice bulanan otomatis dari project retainer. Admin perlu review sebelum dikirim.",
                "terms": "Invoice dibuat otomatis sebagai draft dan perlu disetujui admin sebelum dikirim.",
            },
            actor,
            DocumentStatus.DRAFT,
            PaymentStatus.UNPAID,
            f"Invoice Bulanan {period_tag}",
            lead.business_name,
            project.name,
            "Invoice",
        )
        if doc:
            # Tandai periode di template_name supaya guard idempotensi di run
            # berikutnya bisa mendeteksi invoice periode ini.
            doc.template_name = f"Invoice Bulanan {period_tag}"
            db.flush()
            generated.append(doc)
            create_notification(
                db,
                title="Invoice bulanan dibuat",
                message=f"Draft invoice bulanan untuk {lead.business_name} sudah dibuat.",
                notif_type="invoice",
                target_type="generated_document",
                target_id=doc.id,
                action_url="/documents",
            )
        next_month = due + timedelta(days=30)
        project.next_invoice_date = next_month.isoformat()
    db.commit()
    return generated
