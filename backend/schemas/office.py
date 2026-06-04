from pydantic import BaseModel
from typing import Optional, List


class OfficeChatAttachment(BaseModel):
    name: str
    type: str
    data: str  # base64 data URL


class OfficeChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    attachments: Optional[List[OfficeChatAttachment]] = None


class OfficeAgentCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    soul: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_allowed_users: Optional[str] = None


class OfficeSoulUpdate(BaseModel):
    soul: str


class OfficeEnvUpdate(BaseModel):
    telegram_token: Optional[str] = None
    telegram_allowed_users: Optional[str] = None


class OfficeConfigUpdate(BaseModel):
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None