from pydantic import BaseModel
from typing import Optional


class AdsCampaignIn(BaseModel):
    name: str
    target_audience: str
    budget: float
    drive_link: Optional[str] = None
    status: str = "PLANNING"


class AdsCampaignUpdate(BaseModel):
    name: Optional[str] = None
    target_audience: Optional[str] = None
    budget: Optional[float] = None
    drive_link: Optional[str] = None
    leads_count: Optional[int] = None
    conversions_count: Optional[int] = None
    status: Optional[str] = None


class AdsCampaignOut(BaseModel):
    id: str
    name: str
    target_audience: str
    budget: float
    drive_link: Optional[str] = None
    leads_count: int
    conversions_count: int
    status: str
    created_at: str
    cac: Optional[float] = None
    cost_per_lead: Optional[float] = None
    model_config = {"from_attributes": True}


class BlastCampaignIn(BaseModel):
    name: str
    template_id: Optional[str] = None
    filter_criteria: dict
    scheduled_for: str
    whatsapp_number_id: Optional[str] = None


class BlastCampaignOut(BaseModel):
    id: str
    name: str
    template_id: Optional[str] = None
    filter_criteria: dict
    scheduled_for: str
    status: str
    sent_count: int
    failed_count: int
    whatsapp_number_id: Optional[str] = None
    created_at: str
    model_config = {"from_attributes": True}


class WhatsAppNumberIn(BaseModel):
    label: str
    phone_number: str = ""
    token: str


class WhatsAppNumberUpdate(BaseModel):
    label: Optional[str] = None
    phone_number: Optional[str] = None
    token: Optional[str] = None
    is_active: Optional[bool] = None


class WhatsAppNumberOut(BaseModel):
    id: str
    label: str
    phone_number: str
    token_preview: str = ""
    is_active: bool
    created_at: str
    model_config = {"from_attributes": True}


class FonnteWebhookIn(BaseModel):
    device: Optional[str] = None
    target: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None