import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(255), nullable=False)
    phone_number = Column(String(255), unique=True, nullable=False)
    address = Column(String(255), nullable=True)
    original_url = Column(String(255), nullable=True)
    status = Column(String(255), default="Scraped", nullable=False)
    product_interest = Column(String(255), nullable=True)
    batch_name = Column(String(255), nullable=True)
    rating = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False)
    deleted_at = Column(String(255), nullable=True)
    lead_score = Column(Integer, default=0)
    website_url = Column(String(500), nullable=True)
    google_rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    last_followup_at = Column(String(255), nullable=True)
    sales_owner = Column(String(255), nullable=True)
    next_action_at = Column(String(255), nullable=True)
    loss_reason = Column(String(500), nullable=True)
    do_not_contact = Column(Boolean, default=False, nullable=False)


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=True)
    phone_number = Column(String(255), unique=True, nullable=False)
    purchased_product = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    # FK to Lead - auto-created when Contact is created standalone
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)


class MessageTemplate(Base):
    __tablename__ = "message_templates"
    id = Column(Integer, primary_key=True, index=True)
    product_category = Column(String(255), nullable=False)
    variant_name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)


class ScrapeHistory(Base):
    __tablename__ = "scrape_history"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    product_interest = Column(String(255), nullable=True)
    results_count = Column(Integer, default=0)
    scraped_at = Column(String(255), nullable=False)
    batch_name = Column(String(255), nullable=True)


class LeadActivityLog(Base):
    __tablename__ = "lead_activity_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    activity_type = Column(String(255), nullable=False)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class LeadAnalysis(Base):
    __tablename__ = "lead_analyses"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    analysis = Column(Text, nullable=False)
    pain_points = Column(Text, nullable=True)
    suggested_product = Column(String(255), nullable=True)
    analyzed_at = Column(String(255), nullable=False)
    lead = relationship("Lead", foreign_keys=[lead_id])


class FollowUpSequence(Base):
    __tablename__ = "followup_sequences"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    template_ids = Column(Text, nullable=False, default="[]")
    delays = Column(Text, nullable=False, default="[1,3,7]")
    current_step = Column(Integer, default=0)
    status = Column(String(255), default="ACTIVE")
    started_at = Column(String(255), nullable=False)
    next_send_at = Column(String(255), nullable=True)
    stopped_reason = Column(String(255), nullable=True)


class ReengagementAlert(Base):
    __tablename__ = "reengagement_alerts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    proposal_id = Column(String(36), ForeignKey("proposals.id"), nullable=False)
    triggered_at = Column(String(255), nullable=False)
    is_read = Column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    actor = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False)  # CREATE, UPDATE, DELETE, RESTORE
    table_name = Column(String(255), nullable=False)
    record_id = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)  # JSON string
