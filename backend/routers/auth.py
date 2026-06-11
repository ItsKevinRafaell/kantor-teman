import re, html as html_mod, random, asyncio, uuid, json, csv, io, base64, hmac, time, httpx
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form, Query, Body
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List, Any
from urllib.parse import urlparse
from models import get_db, log_audit, User
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, hash_password,
    verify_password, _check_login_rate_limit, _record_login_failure, _record_login_success,
    create_token, _mask_secret, SENSITIVE_SETTING_KEYS)

router = APIRouter()

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
    ip = request.client.host if request.client else "unknown"
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

