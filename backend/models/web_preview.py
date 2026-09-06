"""Web preview landing pages untuk lead — dibangun saat blast WA ke lead panas.

Alur: blast → lead berstatus "Prospek Panas" → generate HTML landing dari
template bank (per industri) dengan data lead (nama bisnis, WA) → disimpan
di sini → link publik /wp/{slug} dipasang di pesan WA. Pembukaan link
ditrack (opened_count / first_opened_at) + dicatat ke LeadActivityLog.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text

from .base import Base


class WebPreview(Base):
    __tablename__ = "web_previews"

    id = Column(Integer, primary_key=True, index=True)
    # Slug publik, acak & unguessable (bukan id sekuensial)
    slug = Column(String(64), unique=True, index=True, nullable=False)
    lead_id = Column(Integer, nullable=False, index=True)
    campaign_id = Column(String(36), nullable=True)
    template_key = Column(String(64), nullable=False)
    # HTML final hasil swap — disimpan penuh supaya /wp/{slug} cukup baca DB
    html = Column(Text, nullable=False)
    opened_count = Column(Integer, default=0, nullable=False)
    first_opened_at = Column(String(255), nullable=True)
    last_opened_at = Column(String(255), nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    @staticmethod
    def new_slug() -> str:
        return uuid.uuid4().hex[:24]
