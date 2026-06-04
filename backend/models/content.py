import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class ContentSchedule(Base):
    __tablename__ = "content_schedules"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    schedule_date = Column(String(255), nullable=False)
    google_event_id = Column(String(255), nullable=True)
    status = Column(String(255), nullable=False, default="DRAFT")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class ContentProvider(Base):
    """Config API per image provider (base_url, api_key, model)"""
    __tablename__ = "content_providers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    tool_type = Column(String(50), nullable=False)       # "image"
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=True)
    model = Column(String(255), nullable=False)
    extra_params = Column(Text, nullable=True)            # JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class ContentSession(Base):
    """Grouping generasi dalam satu kampanye"""
    __tablename__ = "content_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    user = relationship("User", backref="content_sessions")


class ContentGeneration(Base):
    """Setiap hasil generate"""
    __tablename__ = "content_generations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(36), ForeignKey("content_sessions.id"), nullable=True)
    tool_type = Column(String(50), nullable=False)       # "image" | "caption" | "seo_article"
    input_data = Column(Text, nullable=False)            # JSON
    output_data = Column(Text, nullable=True)            # JSON
    model_used = Column(String(255), nullable=True)
    provider_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    error_msg = Column(Text, nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    user = relationship("User", backref="content_generations")
    session = relationship("ContentSession", backref="generations")
