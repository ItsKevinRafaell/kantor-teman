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
from models import Base, engine, SessionLocal, get_db, log_audit, User, Lead, Contact, Project, Proposal, ProposalAnalytics, Transaction, Wallet, Subscription, PaymentMethod, AuditLog, Board, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity, WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell, WorkspaceAttachment, DynamicTemplate, Document, DocumentFolder, DocumentTemplate, GeneratedDocument, BrandKit, BrandAsset, DocumentSequence, ServiceItem, Category, Product, ClientNote, ClientCredential, ClientDocument, AdsCampaign, BlastCampaign, BlastMessage, FollowUpSequence, MessageTemplate, ScrapeHistory, LeadActivityLog, LeadAnalysis, AIProxy, ContentProvider, ContentSession, ContentGeneration, SystemSettings, AIModel, ProviderConfig, ContentSchedule
from schemas import *
from app.core.dependencies import (get_current_user, require_admin, UPLOADS_DIR,
    HERMES_GATEWAY_URL, _hermes_headers, _office_profile)

router = APIRouter()

@router.post("/api/office/chat/{profile}")
async def office_chat(profile: str, body: OfficeChatRequest, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        raise HTTPException(status_code=503, detail="Hermes gateway not configured")
    profile = _office_profile(profile)
    payload = {"message": body.message, "session_id": body.session_id}
    if body.attachments:
        payload["attachments"] = [a.model_dump() for a in body.attachments]
    async with httpx.AsyncClient(timeout=130) as client:
        resp = await client.post(
            f"{HERMES_GATEWAY_URL}/api/office/chat/{profile}",
            headers=_hermes_headers(),
            json=payload,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Hermes error: {resp.text[:200]}")
    return resp.json()



@router.get("/api/office/status")
async def office_status(current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return {}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/status", headers=_hermes_headers())
            return resp.json()
        except Exception:
            return {}



@router.get("/api/office/history/{profile}")
async def office_history(profile: str, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return []
    profile = _office_profile(profile)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/api/office/history/{profile}", headers=_hermes_headers())
            return resp.json()
        except Exception:
            return []



@router.get("/api/office/timeline/{profile}")
async def office_timeline(profile: str, after: int = -1, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return {"events": [], "next_cursor": after, "has_more": False, "pending_approval_count": 0}
    profile = _office_profile(profile)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{HERMES_GATEWAY_URL}/api/office/timeline/{profile}",
                params={"after": after},
                headers=_hermes_headers()
            )
            return resp.json()
        except Exception:
            return {"events": [], "next_cursor": after, "has_more": False, "pending_approval_count": 0}



@router.get("/api/office/conversations/{profile}")
async def office_conversations(profile: str, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return []
    profile = _office_profile(profile)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/api/office/conversations/{profile}", headers=_hermes_headers())
            return resp.json()
        except Exception:
            return []



@router.get("/api/office/conversations/{profile}/{session_id}")
async def office_conversation_messages(profile: str, session_id: str, current_user: User = Depends(get_current_user)):
    if not HERMES_GATEWAY_URL:
        return []
    profile = _office_profile(profile)
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/api/office/conversations/{profile}/{session_id}", headers=_hermes_headers())
            return resp.json()
        except Exception:
            return []


# ---------- HR Desk: agent CRUD proxy ----------

class OfficeAgentCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    soul: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_allowed_users: Optional[str] = None


class OfficeSoulUpdate(BaseModel):
    soul: str


class OfficeEnvUpdate(BaseModel):
    telegram_token: Optional[str] = None
    telegram_allowed_users: Optional[str] = None


class OfficeConfigUpdate(BaseModel):
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


def _require_gateway():
    if not HERMES_GATEWAY_URL:
        raise HTTPException(status_code=503, detail="Hermes gateway not configured")



@router.get("/api/office/agents")
async def office_list_agents(current_user: User = Depends(get_current_user)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{HERMES_GATEWAY_URL}/api/office/agents", headers=_hermes_headers())
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))



@router.post("/api/office/agents")
async def office_create_agent(body: OfficeAgentCreate, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{HERMES_GATEWAY_URL}/api/office/agents",
            headers=_hermes_headers(),
            json=body.model_dump(exclude_none=True),
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()



@router.delete("/api/office/agents/{profile}")
async def office_delete_agent(profile: str, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(
            f"{HERMES_GATEWAY_URL}/api/office/agents/{profile}",
            headers=_hermes_headers(),
        )
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()



@router.put("/api/office/agents/{profile}/soul")
async def office_update_soul(profile: str, body: OfficeSoulUpdate, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{HERMES_GATEWAY_URL}/api/office/agents/{profile}/soul",
            headers=_hermes_headers(),
            json={"soul": body.soul},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()



@router.put("/api/office/agents/{profile}/env")
async def office_update_env(profile: str, body: OfficeEnvUpdate, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{HERMES_GATEWAY_URL}/api/office/agents/{profile}/env",
            headers=_hermes_headers(),
            json=body.model_dump(exclude_none=True),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()



@router.put("/api/office/agents/{profile}/config")
async def office_update_config(profile: str, body: OfficeConfigUpdate, current_user: User = Depends(require_admin)):
    _require_gateway()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{HERMES_GATEWAY_URL}/api/office/agents/{profile}/config",
            headers=_hermes_headers(),
            json=body.model_dump(exclude_none=True),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()

