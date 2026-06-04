from pydantic import BaseModel
from typing import Optional, List


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


class ProposalAcceptIn(BaseModel):
    client_name: str
    client_phone: str
    accept_notes: Optional[str] = None


class ProposalRejectIn(BaseModel):
    reason: Optional[str] = None