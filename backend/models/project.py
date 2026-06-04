import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Project(Base):
    __tablename__ = "projects"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)  # FIXED / RETAINER
    status = Column(String(255), default="ACTIVE", nullable=False)  # ACTIVE / COMPLETED / HOLD
    nominal = Column(Float, nullable=False, default=0)
    start_date = Column(String(255), nullable=True)
    end_date = Column(String(255), nullable=True)
    color = Column(String(50), nullable=True, default="yellow")
    is_archived = Column(Boolean, default=False, nullable=False)
    service_type = Column(String(50), nullable=True)
    contract_months = Column(Integer, nullable=True, default=1)
    lead = relationship("Lead", foreign_keys=[lead_id])


class ClientNote(Base):
    __tablename__ = "client_notes"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    timestamp = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    actor = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False)  # BISNIS / TEKNIS / PENTING
    content = Column(Text, nullable=False)
    lead = relationship("Lead", foreign_keys=[lead_id])


class ClientCredential(Base):
    __tablename__ = "client_credentials"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    category = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    fields = Column(Text, nullable=False, default="[]")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    lead = relationship("Lead", foreign_keys=[lead_id])


class ClientDocument(Base):
    __tablename__ = "client_documents"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    title = Column(String(255), nullable=False)
    cloud_url = Column(String(255), nullable=False)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    lead = relationship("Lead", foreign_keys=[lead_id])
