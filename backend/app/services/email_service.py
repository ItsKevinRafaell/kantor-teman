"""Shared email delivery service.

Ekstraksi blok SMTP yang sebelumnya inline di routers/documents.py::email_document
supaya dipakai bersama oleh pengiriman dokumen dan laporan (reports) tanpa duplikasi.
Config SMTP diambil dari SystemSettings (smtp_host/port/user/password/from).
"""
from __future__ import annotations

import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.services.settings_service import _get_setting


def send_pdf_email(
    *,
    db: Session,
    to_email: str,
    pdf_path: str,
    attachment_filename: str,
    subject: str,
    body: str,
    brand_name: str = "Kantor Teman",
    reply_to: Optional[str] = None,
    cc: Optional[str] = None,
) -> dict:
    """Kirim satu PDF sebagai lampiran email via SMTP dari SystemSettings.

    Raises HTTPException(400) kalau SMTP belum dikonfigurasi, atau (404) kalau
    file PDF tidak ada di disk, atau (500) kalau pengiriman SMTP gagal.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="File PDF tidak ada di disk")

    smtp_host = _get_setting("smtp_host", "")
    smtp_port = int(_get_setting("smtp_port", "587") or "587")
    smtp_user = _get_setting("smtp_user", "")
    smtp_pass = _get_setting("smtp_password", "")
    smtp_from = _get_setting("smtp_from", smtp_user)

    if not smtp_host or not smtp_user or not smtp_pass:
        raise HTTPException(status_code=400, detail="SMTP belum dikonfigurasi di Settings")

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = to_email
    if cc:
        msg["Cc"] = cc
    if reply_to:
        msg["Reply-To"] = reply_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{attachment_filename}.pdf"',
        )
        msg.attach(part)

    recipients = [to_email] + ([c.strip() for c in cc.split(",") if c.strip()] if cc else [])

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg, to_addrs=recipients)
        server.quit()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"SMTP send gagal: {e}")

    return {"success": True, "to": to_email, "cc": cc}
