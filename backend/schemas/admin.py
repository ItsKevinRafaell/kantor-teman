from pydantic import BaseModel
from typing import Optional


class SettingsUpdate(BaseModel):
    fonnte_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_model: Optional[str] = None
    google_api_key: Optional[str] = None
    google_calendar_id: Optional[str] = None
    google_service_account_json: Optional[str] = None
    admin_wa: Optional[str] = None
    admin_name: Optional[str] = None
    followup_enabled: Optional[str] = None
    followup_hour: Optional[str] = None
    cms_url: Optional[str] = None
    cms_api_token: Optional[str] = None
    external_lead_api_key: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None


class DataAdminBody(BaseModel):
    password: str