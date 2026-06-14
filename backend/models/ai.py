import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean
from .base import Base


class AIProxy(Base):
    __tablename__ = "ai_proxies"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), default="")
    model = Column(String(255), default="")
    # Kept for database compatibility; runtime provider is always 9router.
    provider = Column(String(50), default="9router", nullable=False)
    feature = Column(String(50), nullable=True, index=True)  # article|analysis, NULL=fallback
    is_active = Column(Boolean, default=False)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class ProviderConfig(Base):
    __tablename__ = "provider_configs"
    id = Column(String(36), primary_key=True)
    provider_name = Column(String(255), nullable=False)
    remaining_quota = Column(Float, default=0)
    monthly_quota = Column(Float, default=0)
    price_per_unit_idr = Column(Float, default=0)
    price_input_token_usd = Column(Float, default=0)
    price_output_token_usd = Column(Float, default=0)


class AIModel(Base):
    __tablename__ = "ai_models"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)  # display name (e.g. "combo-genflow")
    model_id = Column(String(255), nullable=False)  # 9router model/combo ID
    description = Column(Text, nullable=True)
    capabilities = Column(Text, nullable=False, default='["chat"]')  # JSON: ["chat", "image", "article", "analysis"]
    is_active = Column(Integer, default=1)
    is_default_chat = Column(Integer, default=0)
    is_default_image = Column(Integer, default=0)
    is_default_article = Column(Integer, default=0)
    is_default_analysis = Column(Integer, default=0)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
