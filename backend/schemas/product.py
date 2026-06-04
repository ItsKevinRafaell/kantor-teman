from pydantic import BaseModel
from typing import Optional, List


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