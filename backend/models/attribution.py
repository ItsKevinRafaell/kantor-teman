import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from .base import Base


class ClientAttributionGBP(Base):
    """Internal attribution evidence for one lead; never GBP publishing state."""

    __tablename__ = "client_attribution_gbp"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, unique=True, index=True)
    canonical_landing_url = Column(String(2000), nullable=False)
    ga4_measurement_id = Column(String(50), nullable=True)
    conversion_event_name = Column(String(255), nullable=True)
    conversion_event_verified = Column(Boolean, nullable=False, default=False)
    readiness_note = Column(Text, nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat(), onupdate=lambda: datetime.now(timezone.utc).isoformat())
