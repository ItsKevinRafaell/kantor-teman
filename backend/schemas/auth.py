import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional


def _password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password minimal 8 karakter")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password harus mengandung huruf besar")
    if not re.search(r"[0-9]", v):
        raise ValueError("Password harus mengandung angka")
    return v


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
        # Password strength is validated on USER CREATION, not on login.
        # Allow any password for login — auth failure is the gatekeeper.
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


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: str
    password: str = Field(..., max_length=128)
    role: str = "member"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _password_strength(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Format email tidak valid")
        if len(v) > 254:
            raise ValueError("Email terlalu panjang")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in {"admin", "member"}:
            raise ValueError("Role harus admin atau member")
        return v


class UserAdminUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[str] = None
    password: Optional[str] = Field(None, max_length=128)
    role: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _password_strength(v)
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Format email tidak valid")
        if len(v) > 254:
            raise ValueError("Email terlalu panjang")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"admin", "member"}:
            raise ValueError("Role harus admin atau member")
        return v


class PasswordResetRequest(BaseModel):
    email: str
    frontend_url: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Format email tidak valid")
        if len(v) > 254:
            raise ValueError("Email terlalu panjang")
        return v

    @field_validator("frontend_url")
    @classmethod
    def validate_frontend_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().rstrip("/")
        if not v:
            return None
        if not re.match(r"^https://[a-zA-Z0-9.-]+(?::\d+)?$", v):
            raise ValueError("URL frontend tidak valid")
        return v


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=32, max_length=256)
    password: str = Field(..., max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _password_strength(v)
