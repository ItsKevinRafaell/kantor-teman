import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Format email tidak valid")
        if len(v) > 254:
            raise ValueError("Email terlalu panjang")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter")
        if len(v) > 128:
            raise ValueError("Password terlalu panjang")
        return v


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    email: str
    role: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None