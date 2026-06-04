"""Auth Service Layer — extracted from routers/auth.py and app/core/dependencies.py"""
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import bcrypt as _bcrypt
import jwt as _jwt
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from models import User
from app.core.dependencies import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS, SECRET_ENCRYPTION_KEY, SENSITIVE_SETTING_KEYS


# ─── Fernet instance ──────────────────────────────────────────────────────────

_fernet = Fernet(SECRET_ENCRYPTION_KEY.encode())


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_jwt_token(user_id: int, email: str) -> str:
    """Create a JWT token for a user."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return _jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises ValueError if invalid."""
    try:
        payload = _jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        raise ValueError("Token tidak valid atau kadaluarsa")


# ─── Password hashing ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a password using bcrypt."""
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# ─── Credential encryption ───────────────────────────────────────────────────

def encrypt_credential(value: str) -> str:
    """Encrypt a credential value using Fernet."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt_credential(value: str) -> str:
    """Decrypt a credential value using Fernet."""
    return _fernet.decrypt(value.encode()).decode()


# ─── Login rate limiting ──────────────────────────────────────────────────────

LOGIN_RATE_MAX = 5
LOGIN_RATE_WINDOW = 300
LOGIN_LOCKOUT_SECONDS = 900

_login_attempts: dict[str, list[float]] = {}
_login_locked_until: dict[str, float] = {}


def check_login_rate_limit(ip: str) -> None:
    """
    Check if IP is rate-limited. Raises ValueError if locked.
    Raises HTTPException via the caller (router) for HTTP response.
    """
    now = time.time()
    locked_until = _login_locked_until.get(ip)
    if locked_until and locked_until > now:
        retry = int(locked_until - now)
        raise ValueError(f"Terlalu banyak percobaan login. Coba lagi dalam {retry} detik.")
    if locked_until and locked_until <= now:
        _login_locked_until.pop(ip, None)
        _login_attempts.pop(ip, None)


def record_login_failure(ip: str) -> None:
    """Record a failed login attempt. Locks IP after LOGIN_RATE_MAX attempts."""
    now = time.time()
    attempts = [t for t in _login_attempts.get(ip, []) if now - t < LOGIN_RATE_WINDOW]
    attempts.append(now)
    _login_attempts[ip] = attempts
    if len(attempts) >= LOGIN_RATE_MAX:
        _login_locked_until[ip] = now + LOGIN_LOCKOUT_SECONDS


def record_login_success(ip: str) -> None:
    """Clear login attempts and lockout after successful login."""
    _login_attempts.pop(ip, None)
    _login_locked_until.pop(ip, None)


# ─── Full authentication flow ─────────────────────────────────────────────────

def authenticate_user(db: Session, email: str, password: str, ip: str) -> Tuple[User, dict]:
    """
    Full authentication flow:
    1. Check rate limit
    2. Verify credentials
    3. Record success/failure
    4. Return (user, token_metadata)
    """
    # Check rate limit
    check_login_rate_limit(ip)

    # Verify user and password
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        record_login_failure(ip)
        raise ValueError("Email atau password salah")

    # Record success
    record_login_success(ip)

    # Create token
    token = create_jwt_token(user.id, user.email)
    metadata = {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }
    return user, metadata


# ─── Password masking (for settings display) ─────────────────────────────────

def mask_secret(value: str) -> str:
    """Mask a secret value for safe display."""
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]


def is_sensitive_key(key: str) -> bool:
    """Check if a setting key is considered sensitive."""
    return key in SENSITIVE_SETTING_KEYS