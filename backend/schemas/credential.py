from pydantic import BaseModel
from typing import Optional, List


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