"""
DB-backed rate limiter — replaces in-memory dicts in app/core/security.py.
Uses naive UTC datetimes for SQLite compatibility.
"""
import time
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.rate_limit import RateLimit
from app.core.config import (
    LOGIN_RATE_MAX,
    LOGIN_RATE_WINDOW,
    LOGIN_LOCKOUT_SECONDS,
)


def _now_naive() -> datetime:
    """Return naive UTC datetime for SQLite compatibility."""
    return datetime.utcnow()


def check_login_rate_limit(ip: str, db: Session):
    now = _now_naive()
    cutoff = now - timedelta(seconds=LOGIN_RATE_WINDOW)

    # Check for active lockout
    lockout = db.query(RateLimit).filter(
        RateLimit.ip == ip,
        RateLimit.key == "lockout",
        RateLimit.ts > cutoff,
    ).first()
    if lockout:
        # lockout.ts is stored as naive UTC
        lockout_ts = lockout.ts
        if hasattr(lockout_ts, 'tzinfo') and lockout_ts.tzinfo is not None:
            lockout_ts = lockout_ts.replace(tzinfo=None)
        retry = max(1, int((lockout_ts - now).total_seconds()))
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan login. Coba lagi dalam {retry} detik.",
            headers={"Retry-After": str(retry)},
        )

    # Clean up expired records
    db.query(RateLimit).filter(
        RateLimit.ip == ip,
        RateLimit.key == "attempt",
        RateLimit.ts <= cutoff,
    ).delete()
    db.commit()


def record_login_failure(ip: str, db: Session):
    now = _now_naive()
    # Remove old attempts
    cutoff = now - timedelta(seconds=LOGIN_RATE_WINDOW)
    db.query(RateLimit).filter(
        RateLimit.ip == ip,
        RateLimit.key == "attempt",
        RateLimit.ts <= cutoff,
    ).delete()

    db.add(RateLimit(ip=ip, key="attempt", ts=now))
    db.commit()

    # Count recent attempts
    recent = db.query(RateLimit).filter(
        RateLimit.ip == ip,
        RateLimit.key == "attempt",
        RateLimit.ts > cutoff,
    ).count()

    if recent >= LOGIN_RATE_MAX:
        lockout_until = now + timedelta(seconds=LOGIN_LOCKOUT_SECONDS)
        db.add(RateLimit(ip=ip, key="lockout", ts=lockout_until))
        db.commit()


def record_login_success(ip: str, db: Session):
    db.query(RateLimit).filter(
        RateLimit.ip == ip,
        RateLimit.key.in_(["attempt", "lockout"]),
    ).delete()
    db.commit()


def check_simple_rate_limit(key: str, max_requests: int, window_seconds: int, db: Session):
    now = _now_naive()
    cutoff = now - timedelta(seconds=window_seconds)

    db.query(RateLimit).filter(
        RateLimit.key == key,
        RateLimit.ts <= cutoff,
    ).delete()

    count = db.query(RateLimit).filter(
        RateLimit.key == key,
        RateLimit.ts > cutoff,
    ).count()

    if count >= max_requests:
        oldest = db.query(RateLimit).filter(
            RateLimit.key == key,
        ).order_by(RateLimit.ts.asc()).first()
        if oldest:
            oldest_ts = oldest.ts
            if hasattr(oldest_ts, 'tzinfo') and oldest_ts.tzinfo is not None:
                oldest_ts = oldest_ts.replace(tzinfo=None)
            elapsed = (now - oldest_ts).total_seconds()
            retry = max(1, int(window_seconds - elapsed))
        else:
            retry = window_seconds
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit tercapai. Coba lagi dalam {retry} detik.",
            headers={"Retry-After": str(max(retry, 1))},
        )

    db.add(RateLimit(key=key, ts=now))
    db.commit()
