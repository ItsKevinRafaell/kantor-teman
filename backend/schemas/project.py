from pydantic import BaseModel, Field
from typing import Optional


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