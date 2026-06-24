"""Profile-related Pydantic models."""
from typing import Optional

from pydantic import BaseModel, Field


class ProfileConfig(BaseModel):
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class ProfileStatus(BaseModel):
    profile: str
    runtime_profile: str
    display_name: str
    model: str
    combo: str
    base_url: str
    api_key_configured: bool
    config_path: str
    state: str  # "online" or "offline"


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=31)
    display_name: str = Field("", max_length=64)
    description: str = Field("", max_length=200)
    model: str = Field("", max_length=128)
    base_url: str = Field("", max_length=256)
    api_key: str = Field("", max_length=256)
    soul: str = Field("", max_length=20000)
    telegram_token: str = Field("", max_length=128)
    telegram_allowed_users: str = Field("", max_length=512)


class SoulUpdate(BaseModel):
    soul: str = Field(..., max_length=20000)


class EnvUpdate(BaseModel):
    telegram_token: Optional[str] = Field(None, max_length=128)
    telegram_allowed_users: Optional[str] = Field(None, max_length=512)


class ConfigUpdate(BaseModel):
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class HermesAgentConfigUpdate(BaseModel):
    model: Optional[str] = Field(None, max_length=200)
    combo: Optional[str] = Field(None, max_length=200)
    base_url: Optional[str] = Field(None, max_length=300)
    api_key: Optional[str] = Field(None, max_length=500)
    restart: bool = False


class HermesApplyAllRequest(BaseModel):
    model: Optional[str] = Field(None, max_length=200)
    combo: Optional[str] = Field(None, max_length=200)
    base_url: Optional[str] = Field(None, max_length=300)
    api_key: Optional[str] = Field(None, max_length=500)
    restart: bool = False
