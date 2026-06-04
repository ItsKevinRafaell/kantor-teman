from pydantic import BaseModel
from typing import Optional, List


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