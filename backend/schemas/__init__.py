from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any

class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Format email tidak valid")
        if len(v) > 254:
            raise ValueError("Email terlalu panjang")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter")
        if len(v) > 128:
            raise ValueError("Password terlalu panjang")
        return v



class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    email: str
    role: str



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
    sales_owner: Optional[str] = None
    next_action_at: Optional[str] = None
    loss_reason: Optional[str] = None
    do_not_contact: bool = False
    model_config = {"from_attributes": True}



class ContactOut(BaseModel):
    id: int
    business_name: str
    owner_name: Optional[str]
    phone_number: str
    purchased_product: Optional[str]
    notes: Optional[str]
    model_config = {"from_attributes": True}



class ContactUpdate(BaseModel):
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    owner_name: Optional[str] = None
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
    product_category: str
    min_rating: int = 0
    template_id: Optional[str] = None



class RatingUpdate(BaseModel):
    rating: int



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



class UserUpdate(BaseModel):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None



class ServiceDetail(BaseModel):
    name: str
    price: float
    features: List[str]



class TimelineItem(BaseModel):
    sequence: int
    title: str
    description: str



class ProposalIn(BaseModel):
    lead_id: int
    services: List[ServiceDetail]
    additional_options: Optional[str] = None
    timeline_data: Optional[List[TimelineItem]] = None
    source: Optional[str] = None
    roi_data: Optional[dict] = None



class ProposalOut(BaseModel):
    id: str
    lead_id: int
    services_detail: List[ServiceDetail]
    total_price: float
    additional_options: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    slug: Optional[str] = None
    timeline_data: Optional[List[TimelineItem]] = None
    roi_data: Optional[dict] = None
    model_config = {"from_attributes": True}



class ServiceItemIn(BaseModel):
    name: str
    default_price: float
    default_features: List[str]



class ServiceItemOut(BaseModel):
    id: str
    name: str
    default_price: float
    default_features: List[str]
    model_config = {"from_attributes": True}



class TrackOpenIn(BaseModel):
    proposal_id: str



class TrackPingIn(BaseModel):
    analytics_id: str
    seconds: int = 5
    sections_viewed: List[str] = []



class AnalyticsOut(BaseModel):
    id: str
    proposal_id: str
    opened_at: str
    last_ping: Optional[str] = None
    total_time_seconds: int
    sections_viewed: List[str]
    model_config = {"from_attributes": True}



class WalletIn(BaseModel):
    name: str
    balance: float = 0
    icon: Optional[str] = None
    color: Optional[str] = None



class CategoryIn(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True



class CategoryOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    model_config = {"from_attributes": True}



class ProductIn(BaseModel):
    name: str
    description: Optional[str] = None
    base_price: float
    features: List[str] = []
    category_id: Optional[str] = None
    is_active: bool = True
    is_retainer: bool = False



class ProductOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    base_price: float
    features: List[str]
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    is_active: bool
    is_retainer: bool = False
    model_config = {"from_attributes": True}



class DynamicTemplateIn(BaseModel):
    name: str
    type: str
    content: str
    is_active: bool = True
    category_id: Optional[str] = None



class DynamicTemplateOut(BaseModel):
    id: str
    name: str
    type: str
    content: str
    is_active: bool
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    model_config = {"from_attributes": True}



class WalletOut(BaseModel):
    id: int
    name: str
    balance: float
    icon: Optional[str] = None
    color: Optional[str] = None
    model_config = {"from_attributes": True}



class TransactionIn(BaseModel):
    wallet_id: int
    type: str  # income / expense
    amount: float
    category: Optional[str] = None
    date: str
    notes: Optional[str] = None
    lead_id: Optional[int] = None
    is_billed: bool = False



class TransactionOut(BaseModel):
    id: int
    wallet_id: int
    type: str
    amount: float
    category: Optional[str] = None
    date: str
    notes: Optional[str] = None
    lead_id: Optional[int] = None
    is_billed: bool
    lead_name: Optional[str] = None
    model_config = {"from_attributes": True}



class SubscriptionIn(BaseModel):
    wallet_id: int
    name: str
    amount: float
    billing_cycle: str = "monthly"
    next_billing_date: str
    is_active: bool = True



class SubscriptionOut(BaseModel):
    id: int
    wallet_id: int
    name: str
    amount: float
    billing_cycle: str
    next_billing_date: str
    is_active: bool
    wallet_name: Optional[str] = None
    model_config = {"from_attributes": True}



class PaymentMethodIn(BaseModel):
    name: str = Field(..., max_length=255)
    account_number: Optional[str] = Field(None, max_length=255)
    account_name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    is_active: bool = True
    position: int = 0



class PaymentMethodOut(BaseModel):
    id: int
    name: str
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    position: int
    model_config = {"from_attributes": True}



class FinanceReportOut(BaseModel):
    total_balance: float
    break_even_point: float
    financial_runway_months: float
    expense_by_category: List[dict]



class ProjectIn(BaseModel):
    lead_id: Optional[int] = None
    name: str = Field(..., max_length=200)
    type: str = Field(..., max_length=20)
    status: str = Field("ACTIVE", max_length=20)
    nominal: float = 0
    start_date: Optional[str] = Field(None, max_length=30)
    end_date: Optional[str] = Field(None, max_length=30)
    color: Optional[str] = Field("yellow", max_length=30)
    service_type: Optional[str] = Field(None, max_length=50)
    contract_months: Optional[int] = None



class ProjectOut(BaseModel):
    id: str
    lead_id: Optional[int] = None
    name: str
    type: str
    status: str
    nominal: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    color: Optional[str] = "yellow"
    is_archived: bool = False
    service_type: Optional[str] = None
    contract_months: Optional[int] = None
    model_config = {"from_attributes": True}



class ClientNoteIn(BaseModel):
    lead_id: int
    category: str = Field(..., max_length=20)
    content: str = Field(..., max_length=5000)



class ClientNoteOut(BaseModel):
    id: str
    lead_id: int
    timestamp: str
    actor: str
    category: str
    content: str
    model_config = {"from_attributes": True}



class LeadMin(BaseModel):
    id: int
    business_name: str
    model_config = {"from_attributes": True}



class BoardCardCommentOut(BaseModel):
    id: str
    card_id: str
    author: str
    content: str
    created_at: str
    model_config = {"from_attributes": True}



class BoardCardChecklistOut(BaseModel):
    id: str
    card_id: str
    text: str
    is_done: bool
    position: int
    model_config = {"from_attributes": True}



class BoardCardActivityOut(BaseModel):
    id: str
    card_id: str
    action: str
    description: str
    actor: str
    created_at: str
    model_config = {"from_attributes": True}



class BoardCardOut(BaseModel):
    id: str
    column_id: str
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[list[str]] = []
    position: int
    is_archived: bool
    created_at: str
    updated_at: Optional[str] = None
    lead_id: Optional[int] = None
    lead: Optional[LeadMin] = None
    color: Optional[str] = "yellow"
    is_workspace_linked: bool = False
    comments: list[BoardCardCommentOut] = []
    checklist: list[BoardCardChecklistOut] = []
    activity: list[BoardCardActivityOut] = []
    model_config = {"from_attributes": True}



class BoardColumnOut(BaseModel):
    id: str
    board_id: str
    name: str
    position: int
    color: Optional[str] = "yellow"
    cards: list[BoardCardOut] = []
    model_config = {"from_attributes": True}



class BoardOut(BaseModel):
    id: str
    project_id: str
    created_at: str
    color: Optional[str] = "yellow"
    columns: list[BoardColumnOut] = []
    model_config = {"from_attributes": True}



class BoardColumnIn(BaseModel):
    name: str
    position: Optional[int] = None
    color: Optional[str] = "yellow"



class BoardCardIn(BaseModel):
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[list[str]] = []
    lead_id: Optional[int] = None
    color: Optional[str] = "yellow"



class BoardCardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[list[str]] = None
    column_id: Optional[str] = None
    position: Optional[int] = None
    is_archived: Optional[bool] = None
    lead_id: Optional[int] = None
    color: Optional[str] = None



class MoveCardRequest(BaseModel):
    column_id: str
    position: Optional[int] = None



class BoardCardCommentIn(BaseModel):
    content: str



class BoardCardChecklistIn(BaseModel):
    text: str



class CredentialFieldIn(BaseModel):
    key: str
    value: str
    is_secret: bool = False



class CredentialIn(BaseModel):
    lead_id: Optional[int] = None
    category: str
    title: str
    fields: list[CredentialFieldIn]



class CredentialFieldOut(BaseModel):
    key: str
    value: str
    is_secret: bool = False



class CredentialOut(BaseModel):
    id: str
    lead_id: Optional[int] = None
    category: str
    title: str
    fields: list[CredentialFieldOut]
    created_at: str
    model_config = {"from_attributes": True}



class CredentialUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    fields: Optional[list[CredentialFieldIn]] = None



class DocumentIn(BaseModel):
    lead_id: Optional[int] = None
    title: str
    cloud_url: str



class DocumentOut(BaseModel):
    id: str
    lead_id: Optional[int] = None
    title: str
    cloud_url: str
    created_at: str
    model_config = {"from_attributes": True}



class ExternalLeadIn(BaseModel):
    business_name: str
    phone_number: str
    email: Optional[str] = None
    message: Optional[str] = None
    product_interest: Optional[str] = None
    source: str = "website_temanumkmkita"

    @field_validator("source")
    @classmethod
    def cap_source(cls, v: str) -> str:
        return v[:64]

    @field_validator("message")
    @classmethod
    def cap_message(cls, v: Optional[str]) -> Optional[str]:
        return v[:500] if v else v



class DataAdminBody(BaseModel):
    password: str



class AIModelIn(BaseModel):
    name: str
    model_id: str
    description: Optional[str] = None
    capabilities: List[str] = ["chat"]
    is_active: bool = True



class AIModelOut(BaseModel):
    id: str
    name: str
    model_id: str
    description: Optional[str]
    capabilities: List[str]
    is_active: bool
    is_default_chat: bool
    is_default_image: bool
    is_default_article: bool
    is_default_analysis: bool



class LeadCreate(BaseModel):
    business_name: str = Field(..., max_length=200)
    phone_number: str = Field(..., max_length=30)
    address: Optional[str] = Field(None, max_length=500)
    product_interest: Optional[str] = Field(None, max_length=100)
    batch_name: Optional[str] = Field(None, max_length=100)



class LeadEdit(BaseModel):
    business_name: Optional[str] = Field(None, max_length=200)
    phone_number: Optional[str] = Field(None, max_length=30)
    address: Optional[str] = Field(None, max_length=500)
    product_interest: Optional[str] = Field(None, max_length=100)
    batch_name: Optional[str] = Field(None, max_length=100)



class WaSendIn(BaseModel):
    lead_id: int
    message: str



class ProposalAcceptIn(BaseModel):
    client_name: str
    client_phone: str
    accept_notes: Optional[str] = None



class ProposalRejectIn(BaseModel):
    reason: Optional[str] = None



class TrackActivityBody(BaseModel):
    activity_type: str



class ViewDurationIn(BaseModel):
    duration_seconds: int

    @field_validator("duration_seconds")
    @classmethod
    def cap_duration(cls, v: int) -> int:
        return max(0, min(v, 3600))



class BrandKitUpdate(BaseModel):
    kit_name: Optional[str] = None
    is_active: Optional[bool] = None



class BrandAssetIn(BaseModel):
    asset_type: str
    name: str
    value: Optional[str] = None
    file_url: Optional[str] = None
    position: Optional[int] = 0
    asset_metadata: Optional[str] = None



class DocumentTemplateIn(BaseModel):
    name: str
    type: str
    html_template: str
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = True



class DocumentGenerateIn(BaseModel):
    template_id: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    variables: dict = Field(default_factory=dict)



class DocumentEmailIn(BaseModel):
    to_email: str
    subject: Optional[str] = None
    body: Optional[str] = None



class InvoiceSequenceIn(BaseModel):
    start_from: int = Field(..., ge=1)
    template_type: str = "invoice"



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



class ContentScheduleIn(BaseModel):
    title: str
    type: str
    schedule_date: str
    status: str = "DRAFT"



class ContentScheduleUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    schedule_date: Optional[str] = None
    status: Optional[str] = None



class ContentScheduleOut(BaseModel):
    id: str
    title: str
    type: str
    schedule_date: str
    google_event_id: Optional[str] = None
    status: str
    created_at: str
    model_config = {"from_attributes": True}



class ProviderConfigOut(BaseModel):
    id: str
    provider_name: str
    remaining_quota: float
    price_per_unit_idr: float
    price_input_token_usd: float
    price_output_token_usd: float
    model_config = {"from_attributes": True}



class BlastCampaignIn(BaseModel):
    name: str
    template_id: Optional[str] = None
    filter_criteria: dict
    scheduled_for: str



class BlastCampaignOut(BaseModel):
    id: str
    name: str
    template_id: Optional[str] = None
    filter_criteria: dict
    scheduled_for: str
    status: str
    sent_count: int
    failed_count: int
    created_at: str
    model_config = {"from_attributes": True}



class FonnteWebhookIn(BaseModel):
    device: Optional[str] = None
    target: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None



class WorkspaceInitIn(BaseModel):
    project_id: str
    service_type: str
    contract_months: int = 1
    contract_days: Optional[int] = None



class WorkspaceCellUpdate(BaseModel):
    value_text: Optional[str] = None
    value_bool: Optional[bool] = None
    value_number: Optional[float] = None
    value_date: Optional[str] = None
    value_json: Optional[str] = None



class WorkspaceRowIn(BaseModel):
    cells: dict = {}
    row_order: Optional[int] = None



class WorkspaceColumnIn(BaseModel):
    column_key: str
    column_label: str
    column_type: str = "text"
    column_options: Optional[List[str]] = None
    column_order: Optional[int] = None



class AIProxyIn(BaseModel):
    name: str
    base_url: str
    api_key: str = ""
    model: str = ""
    feature: Optional[str] = None


class AIProxyOut(BaseModel):
    id: str
    name: str
    base_url: str
    api_key: str = ""
    model: str = ""
    feature: Optional[str] = None
    is_active: bool
    created_at: str
    model_config = {"from_attributes": True}


class ContentProviderIn(BaseModel):
    name: str
    tool_type: str = "image"
    base_url: str
    api_key: Optional[str] = None
    model: str
    extra_params: Optional[dict] = None
    is_active: bool = True


class ContentProviderOut(BaseModel):
    id: str
    name: str
    tool_type: str
    base_url: str
    api_key: Optional[str] = None
    model: str
    extra_params: Optional[Any] = None
    is_active: bool
    created_at: str
    model_config = {"from_attributes": True}


class ContentSessionIn(BaseModel):
    name: str
    description: Optional[str] = None


class ContentSessionUpdate(BaseModel):
    name: str
    description: Optional[str] = None


class ContentSessionOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    model_config = {"from_attributes": True}


class ContentGenerationOut(BaseModel):
    id: str
    session_id: Optional[str] = None
    tool_type: str
    input_data: Any = {}
    output_data: Optional[Any] = None
    model_used: Optional[str] = None
    provider_name: Optional[str] = None
    status: str
    error_msg: Optional[str] = None
    created_at: str
    model_config = {"from_attributes": True}


class ImageGenRequest(BaseModel):
    prompt: str
    provider_id: str
    session_id: Optional[str] = None
    negative_prompt: Optional[str] = None
    width: Optional[int] = 512
    height: Optional[int] = 512


class CaptionGenRequest(BaseModel):
    topic: str
    platform: str = "instagram"
    tone: Optional[str] = "casual"
    keywords: Optional[List[str]] = []
    session_id: Optional[str] = None
    context_from: Optional[List[str]] = []


class SeoArticleGenRequest(BaseModel):
    keyword: str
    title: Optional[str] = None
    word_count: Optional[int] = 800
    tone: Optional[str] = "informatif"
    search_intent: Optional[str] = "informational"
    # Semrush data
    keyword_difficulty: Optional[int] = None
    search_volume: Optional[int] = None
    lsi_keywords: Optional[List[str]] = []
    # Content structure
    faq_topics: Optional[List[str]] = []
    serp_features: Optional[List[str]] = []
    # Context
    target_audience: Optional[str] = None
    target_location: Optional[str] = None
    brand_name: Optional[str] = None
    unique_angle: Optional[str] = None
    internal_link_targets: Optional[str] = None
    session_id: Optional[str] = None
    context_from: Optional[List[str]] = []




class CmsPublishRequest(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    meta_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    status: str = "draft"


class ArchiveFolderIn(BaseModel):
    name: str
    parent_id: Optional[str] = None
    color: Optional[str] = "#6B7280"



class ArchiveFolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None
    color: Optional[str] = None



class ArchiveDocIn(BaseModel):
    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = []
    folder_id: Optional[str] = None



class ArchiveDocUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    folder_id: Optional[str] = None



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



