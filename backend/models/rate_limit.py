from sqlalchemy import Column, Integer, String, DateTime, Index
from datetime import datetime, timezone
from .base import Base


class RateLimit(Base):
    """Persisted rate limit records — replaces in-memory dicts."""
    __tablename__ = "rate_limits"
    id = Column(Integer, primary_key=True)
    ip = Column(String(45), nullable=True, index=True)       # IPv6 safe
    key = Column(String(255), nullable=False, index=True)   # endpoint key
    ts = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (Index("ix_rate_limits_key_ts", "key", "ts"),)
