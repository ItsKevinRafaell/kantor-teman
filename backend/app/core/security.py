import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt as _bcrypt
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.core.config import (
    SECRET_ENCRYPTION_KEY,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRE_HOURS,
    LOGIN_RATE_MAX,
    LOGIN_RATE_WINDOW,
    LOGIN_LOCKOUT_SECONDS,
)

_fernet = Fernet(SECRET_ENCRYPTION_KEY.encode())


def encrypt_password(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int, email: str, token_version: int = 1) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        "v": token_version,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# --- Login Rate Limiter ---

_login_attempts: dict[str, list[float]] = defaultdict(list)
_login_locked_until: dict[str, float] = {}


def check_login_rate_limit(ip: str):
    now = time.time()
    locked_until = _login_locked_until.get(ip)
    if locked_until and locked_until > now:
        retry = int(locked_until - now)
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan login. Coba lagi dalam {retry} detik.",
            headers={"Retry-After": str(retry)},
        )
    if locked_until and locked_until <= now:
        _login_locked_until.pop(ip, None)
        _login_attempts.pop(ip, None)


def record_login_failure(ip: str):
    now = time.time()
    attempts = [t for t in _login_attempts[ip] if now - t < LOGIN_RATE_WINDOW]
    attempts.append(now)
    _login_attempts[ip] = attempts
    if len(attempts) >= LOGIN_RATE_MAX:
        _login_locked_until[ip] = now + LOGIN_LOCKOUT_SECONDS


def record_login_success(ip: str):
    _login_attempts.pop(ip, None)
    _login_locked_until.pop(ip, None)


# --- Generic Soft Rate Limiter ---

_rate_buckets: dict[str, list[float]] = defaultdict(list)


def check_simple_rate_limit(key: str, max_requests: int, window_seconds: int):
    now = time.time()
    bucket = [t for t in _rate_buckets[key] if now - t < window_seconds]
    if len(bucket) >= max_requests:
        retry = int(window_seconds - (now - bucket[0]))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit tercapai. Coba lagi dalam {retry} detik.",
            headers={"Retry-After": str(max(retry, 1))},
        )
    bucket.append(now)
    _rate_buckets[key] = bucket
