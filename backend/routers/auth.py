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
from models import get_db, log_audit, User
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, hash_password,
    verify_password, _check_login_rate_limit, _record_login_failure, _record_login_success,
    create_token, _mask_secret, SENSITIVE_SETTING_KEYS)

router = APIRouter()

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
        httponly=True,
        secure=True,
        samesite="none",
        max_age=86400,
        path="/",
        domain=".kantorteman.my.id",
    )
    return TokenOut(
        access_token=token,
        name=user.name,
        email=user.email,
        role=user.role,
    )



@router.post("/api/auth/logout")
def logout(response: Response):
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



