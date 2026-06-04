import uuid
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    services_detail = Column(Text, nullable=False)
    total_price = Column(Float, nullable=False, default=0)
    additional_options = Column(Text, nullable=True)
    status = Column(String(255), default="sent", nullable=False)
    created_at = Column(String(255), nullable=True)
    is_archived = Column(Boolean, default=False)
    deleted_at = Column(String(255), nullable=True)
    slug = Column(String(255), unique=True, nullable=True)
    base_price = Column(Float, nullable=True)
    discount_price = Column(Float, nullable=True)
    discount_expires_at = Column(String(255), nullable=True)
    first_viewed_at = Column(String(255), nullable=True)
    faqs = Column(Text, nullable=True)
    selected_addons = Column(Text, nullable=True, default="[]")
    timeline_data = Column(Text, nullable=True)
    roi_data = Column(Text, nullable=True)
    accepted_at = Column(String(255), nullable=True)
    rejected_at = Column(String(255), nullable=True)
    lead = relationship("Lead", backref="proposals")


class ServiceItem(Base):
    __tablename__ = "service_items"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    default_price = Column(Float, nullable=False)
    default_features = Column(Text, nullable=False)


class ProposalAnalytics(Base):
    __tablename__ = "proposal_analytics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = Column(String(36), ForeignKey("proposals.id"), nullable=False)
    opened_at = Column(String(255), nullable=False)
    last_ping = Column(String(255), nullable=True)
    total_time_seconds = Column(Integer, default=0)
    sections_viewed = Column(Text, default="[]")
    event = Column(String(50), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
