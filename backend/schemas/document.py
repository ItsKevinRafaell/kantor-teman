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
    status: Optional[str] = "Draft"
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


class DocumentWorkflowUpdate(BaseModel):
    status: str
    review_notes: Optional[str] = Field(None, max_length=2000)
    payment_status: Optional[str] = None


class DocumentDraftIn(BaseModel):
    id: Optional[str] = None  # if set, force-update this draft regardless of target combo
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str | int] = None
    variables_json: dict
    line_items_json: Optional[dict] = None

    def model_post_init(self, __context):
        if self.target_id is not None and not isinstance(self.target_id, str):
            self.target_id = str(self.target_id)


class DocumentDraftOut(BaseModel):
    id: str
    template_id: Optional[str]
    template_name: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    variables_json: dict
    created_at: str
    updated_at: Optional[str]
    model_config = {"from_attributes": True}


class DocumentEditIn(BaseModel):
    variables: Optional[dict] = None
    html_content: Optional[str] = None
    change_summary: Optional[str] = None


class DocumentVersionOut(BaseModel):
    id: str
    version_number: int
    variables_json: Optional[dict]
    html_content: Optional[str]
    change_summary: Optional[str]
    created_at: str
    created_by: Optional[str]
    model_config = {"from_attributes": True}
