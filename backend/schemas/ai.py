from pydantic import BaseModel, field_validator
from typing import Optional, List


class AIModelIn(BaseModel):
    name: str
    model_id: str
    description: Optional[str] = None
    capabilities: List[str] = ["chat"]
    is_active: bool = True


class AIModelOut(BaseModel):
    id: str
    name: str
    model_id: str
    description: Optional[str]
    capabilities: List[str]
    is_active: bool
    is_default_chat: bool
    is_default_image: bool
    is_default_article: bool
    is_default_analysis: bool


class AIProxyIn(BaseModel):
    name: str
    base_url: str
    api_key: str = ""
    model: str = ""
    provider: str = "openai"  # openai, claude, gemini
    feature: Optional[str] = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        valid = {"openai", "claude", "gemini"}
        if v not in valid:
            raise ValueError(f"Provider must be one of: {', '.join(sorted(valid))}")
        return v


class AIProxyOut(BaseModel):
    id: str
    name: str
    base_url: str
    api_key: str = ""
    model: str = ""
    provider: str = "openai"
    feature: Optional[str] = None
    is_active: bool
    created_at: str
    model_config = {"from_attributes": True}


class ProviderConfigOut(BaseModel):
    id: str
    provider_name: str
    remaining_quota: float
    price_per_unit_idr: float
    price_input_token_usd: float
    price_output_token_usd: float
    model_config = {"from_attributes": True}