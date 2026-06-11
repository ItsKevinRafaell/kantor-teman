from pydantic import BaseModel
from typing import Optional, List


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


class BoardCardAttachmentOut(BaseModel):
    id: str
    card_id: str
    file_path: str
    file_name: str
    file_type: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: str
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
    color: Optional[str] = "gray"
    is_workspace_linked: bool = False
    comments: list[BoardCardCommentOut] = []
    checklist: list[BoardCardChecklistOut] = []
    activity: list[BoardCardActivityOut] = []
    attachments: list[BoardCardAttachmentOut] = []
    model_config = {"from_attributes": True}


class BoardColumnOut(BaseModel):
    id: str
    board_id: str
    name: str
    position: int
    color: Optional[str] = "gray"
    cards: list[BoardCardOut] = []
    model_config = {"from_attributes": True}


class BoardOut(BaseModel):
    id: str
    project_id: str
    created_at: str
    color: Optional[str] = "gray"
    columns: list[BoardColumnOut] = []
    model_config = {"from_attributes": True}


class BoardColumnIn(BaseModel):
    name: str
    position: Optional[int] = None
    color: Optional[str] = "gray"


class BoardCardIn(BaseModel):
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[list[str]] = []
    lead_id: Optional[int] = None
    color: Optional[str] = "gray"


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
