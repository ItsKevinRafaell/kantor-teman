from pydantic import BaseModel, Field
from typing import Optional, List


class ProjectIn(BaseModel):
    lead_id: Optional[int] = None
    contact_id: Optional[int] = None  # Alternative to lead_id - resolves to lead_id
    name: str = Field(..., max_length=200)
    type: str = Field(..., max_length=20)
    status: str = Field("ACTIVE", max_length=20)
    nominal: float = 0
    start_date: Optional[str] = Field(None, max_length=30)
    end_date: Optional[str] = Field(None, max_length=30)
    color: Optional[str] = Field("gray", max_length=30)
    service_type: Optional[str] = Field(None, max_length=50)
    contract_months: Optional[int] = None
    dp_percent: Optional[float] = None
    monthly_invoice_enabled: Optional[bool] = None
    next_invoice_date: Optional[str] = Field(None, max_length=30)


class ProjectOut(BaseModel):
    id: str
    lead_id: Optional[int] = None
    lead_name: Optional[str] = None
    name: str
    type: str
    status: str
    nominal: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    color: Optional[str] = "gray"
    is_archived: bool = False
    service_type: Optional[str] = None
    contract_months: Optional[int] = None
    dp_percent: Optional[float] = None
    monthly_invoice_enabled: bool = False
    next_invoice_date: Optional[str] = None
    completed_at: Optional[str] = None
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


class ProjectRiwayatIn(BaseModel):
    category: str = Field(..., max_length=50)
    content: str = Field(..., max_length=10000)
    attachments: Optional[List[str]] = None


class ProjectRiwayatOut(BaseModel):
    id: str
    project_id: str
    timestamp: str
    actor: str
    category: str
    content: str
    attachments: Optional[List[str]] = None
    model_config = {"from_attributes": True}
