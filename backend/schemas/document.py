from pydantic import BaseModel, Field
from typing import Optional, List


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