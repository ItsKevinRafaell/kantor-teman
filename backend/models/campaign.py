import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from .base import Base


class AdsCampaign(Base):
    __tablename__ = "ads_campaigns"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    target_audience = Column(String(255), nullable=False)
    budget = Column(Float, nullable=False, default=0)
    drive_link = Column(String(255), nullable=True)
    leads_count = Column(Integer, default=0)
    conversions_count = Column(Integer, default=0)
    status = Column(String(255), nullable=False, default="PLANNING")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class WhatsAppNumber(Base):
    """Fonnte device/number. 1 token Fonnte = 1 device = 1 nomor WA.

    Dipakai buat blast: campaign bisa milih kirim pake nomor mana.
    Tanpa pilihan -> fallback ke token legacy di SystemSettings (fonnte_token).
    """
    __tablename__ = "whatsapp_numbers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    label = Column(String(255), nullable=False, default="")
    phone_number = Column(String(50), nullable=False, default="")
    token = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class BlastCampaign(Base):
    __tablename__ = "blast_campaigns"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    template_id = Column(String(36), ForeignKey("dynamic_templates.id"), nullable=True)
    filter_criteria = Column(Text, nullable=False, default="{}")
    scheduled_for = Column(String(255), nullable=False)
    status = Column(String(255), nullable=False, default="PENDING")
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    total_operational_cost_idr = Column(Float, default=0)
    converted_clients_count = Column(Integer, default=0)
    whatsapp_number_id = Column(String(36), nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class BlastMessage(Base):
    __tablename__ = "blast_messages"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String(36), ForeignKey("blast_campaigns.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey("dynamic_templates.id"), nullable=True, index=True)
    phone_number = Column(String(255), nullable=False, index=True)
    sent_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    delivered_at = Column(String(255), nullable=True)
    read_at = Column(String(255), nullable=True)
    replied_at = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="sent")
    error_message = Column(Text, nullable=True)
    whatsapp_number_id = Column(String(36), nullable=True)
