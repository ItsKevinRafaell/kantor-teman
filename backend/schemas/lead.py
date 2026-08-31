from pydantic import BaseModel, Field, field_validator
from typing import Optional


class Business(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    whatsapp_url: Optional[str] = None
    google_rating: Optional[float] = None
    review_count: Optional[int] = None
    website_url: Optional[str] = None


class LeadOut(BaseModel):
    id: int
    business_name: str
    phone_number: str
    address: Optional[str]
    original_url: Optional[str]
    status: str
    product_interest: Optional[str]
    batch_name: Optional[str]
    rating: int = 0
    is_archived: bool = False
    deleted_at: Optional[str] = None
    lead_score: int = 0
    is_ghost_viewer: bool = False
    action_recommendation: Optional[str] = None
    google_rating: Optional[float] = None
    review_count: Optional[int] = None
    website_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    sales_owner: Optional[str] = None
    next_action_at: Optional[str] = None
    loss_reason: Optional[str] = None
    do_not_contact: bool = False
    status_label: Optional[str] = None
    score_adjustment: int = 0
    score_adjustment_reason: Optional[str] = None
    score_updated_at: Optional[str] = None
    model_config = {"from_attributes": True}


class ContactOut(BaseModel):
    id: int
    business_name: str
    owner_name: Optional[str]
    phone_number: str
    email: Optional[str] = None
    address: Optional[str] = None
    purchased_product: Optional[str]
    notes: Optional[str]
    lead_id: Optional[int] = None  # FK to Lead
    model_config = {"from_attributes": True}


class ContactUpdate(BaseModel):
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    owner_name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    purchased_product: Optional[str] = None
    notes: Optional[str] = None


class TemplateIn(BaseModel):
    product_category: str
    variant_name: str
    content: str


class TemplateOut(BaseModel):
    id: int
    product_category: str
    variant_name: str
    content: str
    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: str


class LeadSalesUpdate(BaseModel):
    sales_owner: Optional[str] = Field(None, max_length=255)
    next_action_at: Optional[str] = Field(None, max_length=255)
    loss_reason: Optional[str] = Field(None, max_length=500)
    do_not_contact: Optional[bool] = None


class ProductUpdate(BaseModel):
    product_interest: str


class BlastIn(BaseModel):
    batch_name: str
    product_category: Optional[str] = None
    min_rating: int = 0
    template_id: Optional[str] = None
    filter_criteria: Optional[dict] = None
    whatsapp_number_id: Optional[str] = None


class RatingUpdate(BaseModel):
    rating: int


class ScoreAdjustmentUpdate(BaseModel):
    adjustment: int = Field(0, ge=-50, le=50)
    reason: Optional[str] = Field(None, max_length=500)


class ScoringSettingsUpdate(BaseModel):
    settings: dict = Field(default_factory=dict)


class LeadCreate(BaseModel):
    business_name: str = Field(..., max_length=200)
    phone_number: str = Field(..., max_length=30)
    address: Optional[str] = Field(None, max_length=500)
    product_interest: Optional[str] = Field(None, max_length=100)
    batch_name: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = Field(None, max_length=500)
    original_url: Optional[str] = Field(None, max_length=500)  # GBP / Google Maps URL
    instagram_url: Optional[str] = Field(None, max_length=500)
    facebook_url: Optional[str] = Field(None, max_length=500)
    tiktok_url: Optional[str] = Field(None, max_length=500)
    google_rating: Optional[float] = None
    review_count: Optional[int] = None


class LeadEdit(BaseModel):
    business_name: Optional[str] = Field(None, max_length=200)
    phone_number: Optional[str] = Field(None, max_length=30)
    address: Optional[str] = Field(None, max_length=500)
    product_interest: Optional[str] = Field(None, max_length=100)
    batch_name: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = Field(None, max_length=500)
    original_url: Optional[str] = Field(None, max_length=500)  # GBP / Google Maps URL
    instagram_url: Optional[str] = Field(None, max_length=500)
    facebook_url: Optional[str] = Field(None, max_length=500)
    tiktok_url: Optional[str] = Field(None, max_length=500)
    google_rating: Optional[float] = None
    review_count: Optional[int] = None


class WaSendIn(BaseModel):
    lead_id: int
    message: str


class ExternalLeadIn(BaseModel):
    business_name: str
    phone_number: str
    email: Optional[str] = None
    message: Optional[str] = None
    product_interest: Optional[str] = None
    source: str = "website_temanumkmkita"
    lead_stage: Optional[str] = Field(None, max_length=50)
    lead_score: Optional[int] = Field(None, ge=0, le=100)
    ai_reason: Optional[str] = Field(None, max_length=1000)
    conversation_id: Optional[str] = Field(None, max_length=100)

    @field_validator("source")
    @classmethod
    def cap_source(cls, v: str) -> str:
        return v[:64]

    @field_validator("message")
    @classmethod
    def cap_message(cls, v: Optional[str]) -> Optional[str]:
        return v[:500] if v else v
