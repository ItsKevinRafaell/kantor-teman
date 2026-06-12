import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
import hashlib
import secrets
import smtplib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from urllib.parse import urlparse
from models import get_db, log_audit, PasswordResetToken, SystemSettings, User
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, hash_password,
    verify_password, _check_login_rate_limit, _record_login_failure, _record_login_success,
    create_token, _mask_secret, SENSITIVE_SETTING_KEYS, _check_simple_rate_limit)

router = APIRouter()

RESET_TOKEN_EXPIRE_MINUTES = 60


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


def _setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(SystemSettings).filter_by(key=key).first()
    return row.value if row and row.value else default


def _public_frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "https://kantorteman.my.id").rstrip("/")


def _send_password_reset_email(db: Session, to_email: str, reset_url: str) -> bool:
    smtp_host = _setting(db, "smtp_host")
    smtp_port = int(_setting(db, "smtp_port", "587") or "587")
    smtp_user = _setting(db, "smtp_user")
    smtp_pass = _setting(db, "smtp_password")
    smtp_from = _setting(db, "smtp_from", smtp_user)
    if not smtp_host or not smtp_user or not smtp_pass:
        return False

    msg = MIMEText(
        "\n".join([
            "Halo,",
            "",
            "Ada permintaan reset password untuk akun KantorTeman kamu.",
            "Buka link berikut untuk membuat password baru:",
            reset_url,
            "",
            f"Link berlaku {RESET_TOKEN_EXPIRE_MINUTES} menit. Abaikan email ini kalau kamu tidak meminta reset password.",
        ]),
        "plain",
        "utf-8",
    )
    msg["Subject"] = "Reset password KantorTeman"
    msg["From"] = smtp_from
    msg["To"] = to_email

    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.starttls()
    try:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [to_email], msg.as_string())
    finally:
        server.quit()
    return True

def _auth_cookie_options():
    frontend_url = os.getenv("FRONTEND_URL", "https://kantorteman.my.id")
    parsed = urlparse(frontend_url)
    hostname = parsed.hostname or ""
    secure = parsed.scheme == "https"
    cookie_domain = os.getenv("AUTH_COOKIE_DOMAIN")
    if cookie_domain is None and hostname.endswith("kantorteman.my.id"):
        cookie_domain = ".kantorteman.my.id"
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "none" if secure else "lax",
        "path": "/",
        "domain": cookie_domain or None,
    }

@router.post("/api/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    _check_login_rate_limit(ip)
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        _record_login_failure(ip)
        raise HTTPException(status_code=401, detail="Email atau password salah")
    _record_login_success(ip)
    token = create_token(user.id, user.email)
    response.set_cookie(
        key="kt_token",
        value=token,
        max_age=86400,
        **_auth_cookie_options(),
    )
    return TokenOut(
        access_token=token,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@router.post("/api/auth/password/forgot")
def request_password_reset(body: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    _check_simple_rate_limit(f"password-reset:{ip}", 5, 300)
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        raw_token = secrets.token_urlsafe(32)
        expires_at = _utc_now() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
        db.add(PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            expires_at=expires_at.isoformat(),
            created_at=_utc_now().isoformat(),
        ))
        db.commit()
        reset_url = f"{_public_frontend_url()}/reset-password?token={raw_token}"
        try:
            sent = _send_password_reset_email(db, user.email, reset_url)
            if not sent:
                print("[PASSWORD_RESET] SMTP not configured; reset email not sent.", flush=True)
        except Exception as exc:
            print(f"[PASSWORD_RESET] email failed: {type(exc).__name__}: {exc}", flush=True)
    return {"ok": True, "message": "Jika email terdaftar dan SMTP aktif, instruksi reset password akan dikirim."}


@router.post("/api/auth/password/reset")
def reset_password(body: PasswordResetConfirm, db: Session = Depends(get_db)):
    token_hash = _hash_reset_token(body.token)
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    if not row or row.used_at:
        raise HTTPException(status_code=400, detail="Token reset tidak valid atau sudah dipakai.")
    try:
        expires_at = datetime.fromisoformat(row.expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Token reset tidak valid.")
    if expires_at < _utc_now():
        raise HTTPException(status_code=400, detail="Token reset sudah kedaluwarsa.")
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User tidak ditemukan.")
    user.hashed_password = hash_password(body.password)
    row.used_at = _utc_now().isoformat()
    db.commit()
    return {"ok": True}



@router.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(key="kt_token", **_auth_cookie_options())
    # Also clear legacy production and localhost cookies during rollout.
    response.delete_cookie(key="kt_token", path="/", samesite="none", domain=".kantorteman.my.id", secure=True)
    response.delete_cookie(key="kt_token", path="/", samesite="lax")
    return {"ok": True}


# ---------------------------------------------------------------------------
# User / Settings endpoints
# ---------------------------------------------------------------------------


@router.get("/api/users")
def list_users(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role} for u in users]


def _count_admins(db: Session) -> int:
    return db.query(User).filter(User.role == "admin").count()


@router.post("/api/users", status_code=201)
def create_user(body: UserCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah dipakai")
    user = User(
        name=body.name.strip(),
        email=email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit(db, current_user.name, "CREATE", "users", str(user.id), {"email": user.email, "role": user.role})
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@router.put("/api/users/{user_id}")
def update_user(user_id: int, body: UserAdminUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if body.email is not None:
        email = body.email.strip().lower()
        existing = db.query(User).filter(User.email == email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email sudah dipakai")
        user.email = email
    if body.name is not None:
        user.name = body.name.strip()
    if body.password:
        user.hashed_password = hash_password(body.password)
    if body.role is not None:
        if user.role == "admin" and body.role != "admin" and _count_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="Tidak bisa menurunkan role admin terakhir")
        user.role = body.role
    db.commit()
    db.refresh(user)
    log_audit(db, current_user.name, "UPDATE", "users", str(user.id), {"email": user.email, "role": user.role})
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@router.delete("/api/users/{user_id}", status_code=204)
def delete_user(user_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Tidak bisa menghapus akun sendiri")
    if user.role == "admin" and _count_admins(db) <= 1:
        raise HTTPException(status_code=400, detail="Tidak bisa menghapus admin terakhir")
    log_audit(db, current_user.name, "DELETE", "users", str(user.id), {"email": user.email, "role": user.role})
    db.delete(user)
    db.commit()



@router.get("/api/user/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "name": current_user.name, "email": current_user.email, "role": current_user.role}



@router.put("/api/user/me")
def update_me(body: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user.id).first()
    if body.name:
        user.name = body.name
    if body.new_password:
        if not body.current_password or not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Password lama tidak cocok")
        user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"id": user.id, "name": user.name, "email": user.email}
