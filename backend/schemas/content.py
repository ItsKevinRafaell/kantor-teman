from pydantic import BaseModel, Field
from typing import Optional, List, Any


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