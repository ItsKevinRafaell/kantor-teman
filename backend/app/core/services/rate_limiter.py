"""
DB-backed rate limiter — replaces in-memory dicts in app/core/security.py.
"""
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.rate_limit import RateLimit
from app.core.config import (
    LOGIN_RATE_MAX,
    LOGIN_RATE_WINDOW,
    LOGIN_LOCKOUT_SECONDS,
)


def check_login_rate_limit(ip: str, db: Session):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=LOGIN_RATE_WINDOW)

    # Check for active lockout
    lockout = db.query(RateLimit).filter(
        RateLimit.ip == ip,
        RateLimit.key == "lockout",
        RateLimit.ts > now,
    ).first()
    if lockout:
        retry = int((lockout.ts - now).total_seconds())
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
    now = datetime.now(timezone.utc)
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
    now = datetime.now(timezone.utc)
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
            elapsed = (now - oldest.ts).total_seconds()
            retry = int(window_seconds - elapsed)
        else:
            retry = window_seconds
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit tercapai. Coba lagi dalam {retry} detik.",
            headers={"Retry-After": str(max(retry, 1))},
        )

    db.add(RateLimit(key=key, ts=now))
    db.commit()
