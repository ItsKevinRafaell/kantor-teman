import re
import random
import asyncio
import uuid
import json
import csv
import io
import httpx
from search_volume_data import get_monthly_search_volume
from fastapi import FastAPI, Query, HTTPException, Depends, BackgroundTasks, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Any
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from cryptography.fernet import Fernet
import jwt
import bcrypt as _bcrypt
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, ForeignKey, select, func, DateTime
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship

load_dotenv(os.environ.get("ENV_FILE", ".env.production"))

SECRET_ENCRYPTION_KEY = os.environ["SECRET_ENCRYPTION_KEY"]  # fail hard kalo kosong
_fernet = Fernet(SECRET_ENCRYPTION_KEY.encode())


def encrypt_password(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


app = FastAPI(title="Kantor Teman API")

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://kantorteman.my.id")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "https://kantor-teman-five.vercel.app,https://kantorteman.my.id")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGIN.split(",") if CORS_ORIGIN else [
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")  # boleh kosong
PLACES_NEW_SEARCH_URL = os.environ.get("PLACES_NEW_SEARCH_URL", "https://places.googleapis.com/v1/places:searchText")
JWT_SECRET = os.getenv("JWT_SECRET", "kantor-teman-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# Limit concurrent search to prevent LSAPI worker explosion
search_semaphore = asyncio.Semaphore(1)

bearer_scheme = HTTPBearer()


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leads.db")
# Auto-register PyMySQL for MySQL connections
if "mysql" in DATABASE_URL and "pymysql" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://")
_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
from sqlalchemy.pool import NullPool
engine = create_engine(DATABASE_URL, connect_args=_connect_args, poolclass=NullPool)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)


class SystemSettings(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)


class AIProxy(Base):
    __tablename__ = "ai_proxies"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), default="")
    model = Column(String(255), default="")
    is_active = Column(Boolean, default=False)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(255), nullable=False)
    phone_number = Column(String(255), unique=True, nullable=False)
    address = Column(String(255), nullable=True)
    original_url = Column(String(255), nullable=True)
    status = Column(String(255), default="Scraped", nullable=False)
    product_interest = Column(String(255), nullable=True)
    batch_name = Column(String(255), nullable=True)
    rating = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False)
    deleted_at = Column(String(255), nullable=True)
    lead_score = Column(Integer, default=0)
    website_url = Column(String(500), nullable=True)
    google_rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=True)
    phone_number = Column(String(255), unique=True, nullable=False)
    purchased_product = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)


class MessageTemplate(Base):
    __tablename__ = "message_templates"
    id = Column(Integer, primary_key=True, index=True)
    product_category = Column(String(255), nullable=False)
    variant_name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)


class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    services_detail = Column(Text, nullable=False)
    total_price = Column(Float, nullable=False, default=0)
    additional_options = Column(Text, nullable=True)
    status = Column(String(255), default="Sent", nullable=False)
    created_at = Column(String(255), nullable=True)
    is_archived = Column(Boolean, default=False)
    deleted_at = Column(String(255), nullable=True)
    slug = Column(String(255), unique=True, nullable=True)
    base_price = Column(Float, nullable=True)
    discount_price = Column(Float, nullable=True)
    discount_expires_at = Column(String(255), nullable=True)
    first_viewed_at = Column(String(255), nullable=True)
    faqs = Column(Text, nullable=True)
    selected_addons = Column(Text, nullable=True, default="[]")
    timeline_data = Column(Text, nullable=True)
    roi_data = Column(Text, nullable=True)
    lead = relationship("Lead", backref="proposals")


class ServiceItem(Base):
    __tablename__ = "service_items"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    default_price = Column(Float, nullable=False)
    default_features = Column(Text, nullable=False)


class Category(Base):
    __tablename__ = "categories"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    products = relationship("Product", back_populates="category_rel")


class Product(Base):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Float, nullable=False)
    features = Column(Text, nullable=False, default="[]")
    category = Column(String(255), nullable=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_retainer = Column(Boolean, default=False)
    monthly_ads_cost = Column(Float, nullable=True, default=5000000)
    roi_months = Column(Integer, nullable=True, default=3)
    roi_multiplier = Column(Float, nullable=True, default=3.5)
    comparison_points = Column(Text, nullable=True)
    category_rel = relationship("Category", back_populates="products")


class DynamicTemplate(Base):
    __tablename__ = "dynamic_templates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)  # WA_BLAST, PROPOSAL_TEXT, PROPOSAL_INTRO, PROPOSAL_OUTRO, FOLLOW_UP, GENERAL, TIMELINE_TEMPLATE
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    category_rel = relationship("Category")


class ProposalAnalytics(Base):
    __tablename__ = "proposal_analytics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = Column(String(36), ForeignKey("proposals.id"), nullable=False)
    opened_at = Column(String(255), nullable=False)
    last_ping = Column(String(255), nullable=True)
    total_time_seconds = Column(Integer, default=0)
    sections_viewed = Column(Text, default="[]")


# ---------------------------------------------------------------------------
# Finance Models (Overhead Tracker)
# ---------------------------------------------------------------------------

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    balance = Column(Float, nullable=False, default=0)
    icon = Column(String(255), nullable=True)
    color = Column(String(255), nullable=True)
    transactions = relationship("Transaction", back_populates="wallet")
    subscriptions = relationship("Subscription", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    type = Column(String(255), nullable=False)  # income / expense
    amount = Column(Float, nullable=False)
    category = Column(String(255), nullable=True)
    date = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    is_billed = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    deleted_at = Column(String(255), nullable=True)
    wallet = relationship("Wallet", back_populates="transactions")
    lead = relationship("Lead", foreign_keys=[lead_id])


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    billing_cycle = Column(String(255), nullable=False, default="monthly")  # monthly / yearly
    next_billing_date = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    wallet = relationship("Wallet", back_populates="subscriptions")


# ---------------------------------------------------------------------------
# Audit Log Model
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    actor = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False)  # CREATE, UPDATE, DELETE, RESTORE
    table_name = Column(String(255), nullable=False)
    record_id = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)  # JSON string


class ScrapeHistory(Base):
    __tablename__ = "scrape_history"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    product_interest = Column(String(255), nullable=True)
    results_count = Column(Integer, default=0)
    scraped_at = Column(String(255), nullable=False)


class LeadActivityLog(Base):
    __tablename__ = "lead_activity_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    activity_type = Column(String(255), nullable=False)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class LeadAnalysis(Base):
    __tablename__ = "lead_analyses"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    analysis = Column(Text, nullable=False)
    pain_points = Column(Text, nullable=True)
    suggested_product = Column(String(255), nullable=True)
    analyzed_at = Column(String(255), nullable=False)
    lead = relationship("Lead", foreign_keys=[lead_id])


class Project(Base):
    __tablename__ = "projects"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)  # FIXED / RETAINER
    status = Column(String(255), default="ACTIVE", nullable=False)  # ACTIVE / COMPLETED / HOLD
    nominal = Column(Float, nullable=False, default=0)
    start_date = Column(String(255), nullable=True)
    end_date = Column(String(255), nullable=True)
    color = Column(String(50), nullable=True, default="yellow")
    is_archived = Column(Boolean, default=False, nullable=False)
    lead = relationship("Lead", foreign_keys=[lead_id])


class ClientNote(Base):
    __tablename__ = "client_notes"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    timestamp = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    actor = Column(String(255), nullable=False)
    category = Column(String(255), nullable=False)  # BISNIS / TEKNIS / PENTING
    content = Column(Text, nullable=False)
    lead = relationship("Lead", foreign_keys=[lead_id])


class ClientCredential(Base):
    __tablename__ = "client_credentials"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    category = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    fields = Column(Text, nullable=False, default="[]")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    lead = relationship("Lead", foreign_keys=[lead_id])


class ClientDocument(Base):
    __tablename__ = "client_documents"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    title = Column(String(255), nullable=False)
    cloud_url = Column(String(255), nullable=False)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    lead = relationship("Lead", foreign_keys=[lead_id])


# Board models for Trello-like functionality
class Board(Base):
    __tablename__ = "boards"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    created_at = Column(String(255), default=lambda: datetime.now(timezone.utc).isoformat())
    color = Column(String(50), nullable=True, default="yellow")
    project = relationship("Project", foreign_keys=[project_id])


class BoardColumn(Base):
    __tablename__ = "board_columns"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id = Column(String(36), ForeignKey("boards.id"), nullable=False)
    name = Column(String(255), nullable=False)
    position = Column(Integer, default=0)
    color = Column(String(50), nullable=True, default="yellow")
    board = relationship("Board", foreign_keys=[board_id])


class BoardCard(Base):
    __tablename__ = "board_cards"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    column_id = Column(String(36), ForeignKey("board_columns.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    assignee = Column(String(255), nullable=True)
    due_date = Column(String(255), nullable=True)
    labels = Column(Text, nullable=True)  # JSON array
    position = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False)
    created_at = Column(String(255), default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(255), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    color = Column(String(50), nullable=True, default="yellow")
    column = relationship("BoardColumn", foreign_keys=[column_id])
    lead = relationship("Lead", foreign_keys=[lead_id])


class BoardCardComment(Base):
    __tablename__ = "board_card_comments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String(36), ForeignKey("board_cards.id"), nullable=False)
    author = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(String(255), default=lambda: datetime.now(timezone.utc).isoformat())
    card = relationship("BoardCard", foreign_keys=[card_id], backref="comments")


class BoardCardChecklist(Base):
    __tablename__ = "board_card_checklists"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String(36), ForeignKey("board_cards.id"), nullable=False)
    text = Column(String(255), nullable=False)
    is_done = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    card = relationship("BoardCard", foreign_keys=[card_id], backref="checklist")


class BoardCardActivity(Base):
    __tablename__ = "board_card_activities"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String(36), ForeignKey("board_cards.id"), nullable=False)
    action = Column(String(255), nullable=False)  # created, moved, updated, commented, archived
    description = Column(String(255), nullable=False)
    actor = Column(String(255), nullable=False)
    created_at = Column(String(255), default=lambda: datetime.now(timezone.utc).isoformat())
    card = relationship("BoardCard", foreign_keys=[card_id], backref="activity")


class AdsCampaign(Base):
    __tablename__ = "ads_campaigns"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    target_audience = Column(String(255), nullable=False)
    budget = Column(Float, nullable=False, default=0)
    drive_link = Column(String(255), nullable=True)
    leads_count = Column(Integer, default=0)
    conversions_count = Column(Integer, default=0)
    status = Column(String(255), nullable=False, default="PLANNING")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class BlastCampaign(Base):
    __tablename__ = "blast_campaigns"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    template_id = Column(String(36), ForeignKey("dynamic_templates.id"), nullable=True)
    filter_criteria = Column(Text, nullable=False, default="{}")
    scheduled_for = Column(String(255), nullable=False)
    status = Column(String(255), nullable=False, default="PENDING")
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    total_operational_cost_idr = Column(Float, default=0)
    converted_clients_count = Column(Integer, default=0)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class FollowUpSequence(Base):
    __tablename__ = "followup_sequences"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    template_ids = Column(Text, nullable=False, default="[]")
    delays = Column(Text, nullable=False, default="[1,3,7]")
    current_step = Column(Integer, default=0)
    status = Column(String(255), default="ACTIVE")
    started_at = Column(String(255), nullable=False)
    next_send_at = Column(String(255), nullable=True)
    stopped_reason = Column(String(255), nullable=True)


class ReengagementAlert(Base):
    __tablename__ = "reengagement_alerts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    proposal_id = Column(String(36), ForeignKey("proposals.id"), nullable=False)
    triggered_at = Column(String(255), nullable=False)
    is_read = Column(Boolean, default=False)


class ProviderConfig(Base):
    __tablename__ = "provider_configs"
    id = Column(String(36), primary_key=True)
    provider_name = Column(String(255), nullable=False)
    remaining_quota = Column(Float, default=0)
    monthly_quota = Column(Float, default=0)
    price_per_unit_idr = Column(Float, default=0)
    price_input_token_usd = Column(Float, default=0)
    price_output_token_usd = Column(Float, default=0)


class ContentSchedule(Base):
    __tablename__ = "content_schedules"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    schedule_date = Column(String(255), nullable=False)
    google_event_id = Column(String(255), nullable=True)
    status = Column(String(255), nullable=False, default="DRAFT")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# AI Chat Models (Semuts.sh Integration)
# ---------------------------------------------------------------------------

class ChatProject(Base):
    __tablename__ = "chat_projects"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)
    default_model = Column(String(255), default="glm-5")
    context_window_size = Column(Integer, default=20)  # N pesan terakhir sebagai context
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(255), nullable=True)
    user = relationship("User", backref="chat_projects")


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("chat_projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False, default="New Chat")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(255), nullable=True)
    project = relationship("ChatProject", backref="conversations")
    user = relationship("User", backref="chat_conversations")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    model_used = Column(String(255), nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    conversation = relationship("ChatConversation", backref="messages")


class ChatMemory(Base):
    __tablename__ = "chat_memories"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("chat_projects.id"), nullable=False)
    content = Column(Text, nullable=False)
    pinned_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # user yang pin memory
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    project = relationship("ChatProject", backref="memories")
    user = relationship("User", backref="chat_memories")


class ChatSummary(Base):
    """Store conversation summaries for long context management"""
    __tablename__ = "chat_summaries"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False)
    content = Column(Text, nullable=False)  # Summary text
    message_count = Column(Integer, default=0)  # Number of messages summarized
    tokens_saved = Column(Integer, default=0)  # Estimated tokens saved
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())



# ---------------------------------------------------------------------------
# Content Generator Models
# ---------------------------------------------------------------------------

class ContentProvider(Base):
    """Config API per image provider (base_url, api_key, model)"""
    __tablename__ = "content_providers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    tool_type = Column(String(50), nullable=False)       # "image"
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=True)
    model = Column(String(255), nullable=False)
    extra_params = Column(Text, nullable=True)            # JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class ContentSession(Base):
    """Grouping generasi dalam satu kampanye"""
    __tablename__ = "content_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    user = relationship("User", backref="content_sessions")


class ContentGeneration(Base):
    """Setiap hasil generate"""
    __tablename__ = "content_generations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(36), ForeignKey("content_sessions.id"), nullable=True)
    tool_type = Column(String(50), nullable=False)       # "image" | "caption" | "seo_article"
    input_data = Column(Text, nullable=False)            # JSON
    output_data = Column(Text, nullable=True)            # JSON
    model_used = Column(String(255), nullable=True)
    provider_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    error_msg = Column(Text, nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    user = relationship("User", backref="content_generations")
    session = relationship("ContentSession", backref="generations")


# ---------------------------------------------------------------------------
# Document Folder / Archive Models
# ---------------------------------------------------------------------------

class DocumentFolder(Base):
    __tablename__ = "document_folders"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    parent_id = Column(String(36), ForeignKey("document_folders.id"), nullable=True)
    color = Column(String(20), nullable=False, default="#6B7280")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    user = relationship("User", backref="document_folders")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    folder_id = Column(String(36), ForeignKey("document_folders.id"), nullable=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    url = Column(String(2000), nullable=True)
    tags = Column(Text, nullable=False, default="[]")
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(255), nullable=True)
    user = relationship("User", backref="documents")
    folder = relationship("DocumentFolder", backref="documents")


Base.metadata.create_all(bind=engine)


def _migrate_ai_proxy(db: Session):
    """Create sample AIProxy for NEW PRODUCTION DB ONLY. Manual run."""
    pass  # Disabled


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_audit(db: Session, actor: str, action: str, table_name: str, record_id, details=None):
    entry = AuditLog(
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=actor,
        action=action,
        table_name=table_name,
        record_id=str(record_id),
        details=json.dumps(details) if details else None,
    )
    db.add(entry)
    db.commit()


def seed_data(db: Session):
    if not db.query(User).first():
        db.add(User(
            name="Admin",
            email="admin@kantorteman.com",
            hashed_password=hash_password("admin123"),
        ))
        db.commit()
    if not db.query(SystemSettings).filter_by(key="fonnte_token").first():
        db.add(SystemSettings(key="fonnte_token", value=os.getenv("FONNTE_TOKEN", "")))
        db.commit()
    if not db.query(ProviderConfig).first():
        providers = [
            ProviderConfig(id="FONNTE", provider_name="Fonnte WhatsApp", remaining_quota=10000, price_per_unit_idr=6.6, price_input_token_usd=0, price_output_token_usd=0),
            ProviderConfig(id="GEMINI", provider_name="Gemini 2.5 Flash", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0.000075, price_output_token_usd=0.0003),
            ProviderConfig(id="CLAUDE", provider_name="Claude 4.5 Haiku", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0.00025, price_output_token_usd=0.0125),
            ProviderConfig(id="OPENAI", provider_name="GPT-5", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0.0025, price_output_token_usd=0.010),
        ]
        db.add_all(providers)
        db.commit()

    # Seed Timeline Templates
    if not db.query(DynamicTemplate).filter_by(type="TIMELINE_TEMPLATE").first():
        timeline_templates = [
            DynamicTemplate(
                id="timeline-seo-lokal",
                name="Timeline SEO Lokal",
                type="TIMELINE_TEMPLATE",
                content=json.dumps([
                    {"sequence": 1, "title": "Audit & Riset Kata Kunci", "description": "Analisis kompetitor, riset kata kunci lokal bervolume tinggi, dan audit teknis website existing."},
                    {"sequence": 2, "title": "Optimasi On-Page & Teknis", "description": "Perbaikan struktur website, meta tags, schema markup, dan kecepatan loading halaman."},
                    {"sequence": 3, "title": "Setup Google Business Profile", "description": "Optimasi profil Google Maps, kategori bisnis, foto, dan informasi NAP (Name, Address, Phone)."},
                    {"sequence": 4, "title": "Content & Link Building Lokal", "description": "Pembuatan konten lokal berkualitas dan backlink dari direktori bisnis terpercaya di wilayah target."},
                    {"sequence": 5, "title": "Monitoring & Reporting", "description": "Tracking peringkat, analisis trafik organik, dan laporan performa bulanan dengan rekomendasi lanjutan."},
                ]),
                is_active=True,
                category_id=None,
            ),
            DynamicTemplate(
                id="timeline-web-dev",
                name="Timeline Web Development",
                type="TIMELINE_TEMPLATE",
                content=json.dumps([
                    {"sequence": 1, "title": "Discovery & Wireframe", "description": "Diskusi kebutuhan bisnis, pembuatan sitemap, wireframe UI/UX, dan approval desain awal."},
                    {"sequence": 2, "title": "Desain Visual & Prototype", "description": "Pembuatan desain high-fidelity, pemilihan color scheme, typography, dan interactive prototype."},
                    {"sequence": 3, "title": "Development Frontend & Backend", "description": "Coding halaman responsif, integrasi CMS/database, dan pengembangan fitur custom sesuai kebutuhan."},
                    {"sequence": 4, "title": "Testing & Quality Assurance", "description": "Pengujian fungsional, responsivitas, kecepatan, keamanan, dan kompatibilitas lintas browser/device."},
                    {"sequence": 5, "title": "Launch & Deployment", "description": "Migrasi ke server produksi, setup domain & SSL, konfigurasi SEO dasar, dan go-live monitoring."},
                    {"sequence": 6, "title": "Maintenance & Support", "description": "Dukungan teknis pasca-launch, backup rutin, update keamanan, dan minor revision selama 30 hari."},
                ]),
                is_active=True,
                category_id=None,
            ),
        ]
        db.add_all(timeline_templates)
        db.commit()


"""
Expected env variables (all required in production):
  $JWT_SECRET   — signing key for JWT tokens
  $SECRET_ENCRYPTION_KEY — Fernet key for encrypting stored secrets
  $FRONTEND_URL — https://your-frontend.vercel.app
  $CORS_ORIGIN  — comma-separated allowed origins
  $DATABASE_URL — mysql://user:pass@host/db
"""
# ── Runtime validation ──────────────────────────────────────────────────────

USD_TO_IDR = 17000


def slugify(text: str) -> str:
    text = text.lower().strip()
    # Remove emojis and special unicode characters
    text = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        r'\U0000FE00-\U0000FE0F\U0000200D]+', '', text)
    # Replace dots, spaces, underscores, slashes with hyphens
    text = re.sub(r'[\s._/]+', '-', text)
    # Remove remaining special characters (keep alphanumeric and hyphens)
    text = re.sub(r'[^\w-]', '', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def generate_unique_slug(db: Session, base_text: str) -> str:
    slug = slugify(base_text)
    if not slug:
        slug = "proposal"
    existing = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not existing:
        return slug
    counter = 1
    while True:
        candidate = f"{slug}-{counter}"
        if not db.query(Proposal).filter(Proposal.slug == candidate).first():
            return candidate
        counter += 1


def _build_addons_from_products(db: Session) -> str:
    products = db.query(Product).filter(Product.is_active == True).all()
    addons = [{"id": p.id, "name": p.name, "price": p.base_price} for p in products]
    return json.dumps(addons)


def _build_roi_data(db: Session, services: list, roi_input: dict = None) -> str:
    if not roi_input or not roi_input.get("enabled", True):
        return json.dumps({"enabled": False})

    retainer_period = roi_input.get("retainer_period", 0)
    service_names = [s.name.lower() for s in services]
    products = db.query(Product).filter(Product.is_active == True).all()

    matched = []
    for p in products:
        if any(p.name.lower() in sn or sn in p.name.lower() for sn in service_names):
            matched.append(p)

    if not matched:
        matched = products[:3] if products else []

    if not matched:
        return json.dumps({
            "enabled": True,
            "monthly_ads_cost": 5000000,
            "roi_months": 3,
            "roi_multiplier": 3.5,
            "has_retainer": False,
            "retainer_period": 0,
        })

    has_retainer = any(p.is_retainer for p in matched)
    total_ads_cost = sum(p.monthly_ads_cost or 5000000 for p in matched)
    total_price = sum(s.price for s in services)

    retainer_total = 0
    onetime_total = 0
    for i, p in enumerate(matched):
        price = services[i].price if i < len(services) else p.base_price
        if p.is_retainer:
            retainer_total += price
        else:
            onetime_total += price

    comparison_period = retainer_period if retainer_period > 0 else 12
    our_total_cost = onetime_total + (retainer_total * comparison_period)
    ads_total_cost = total_ads_cost * comparison_period

    weighted_roi_months = sum((p.roi_months or 3) * (p.base_price or 1) for p in matched) / max(1, sum(p.base_price or 1 for p in matched))
    roi_months = max(1, round(weighted_roi_months))

    best_multiplier = max(p.roi_multiplier or 3.5 for p in matched)
    multiplier = round(best_multiplier + (len(matched) - 1) * 0.3, 1)

    if total_price > 0 and total_ads_cost > 0:
        roi_months = max(1, min(roi_months, round(total_price / (total_ads_cost * 0.4))))

    return json.dumps({
        "enabled": True,
        "monthly_ads_cost": total_ads_cost,
        "roi_months": roi_months,
        "roi_multiplier": multiplier,
        "has_retainer": has_retainer,
        "retainer_period": retainer_period,
        "retainer_monthly": retainer_total,
        "onetime_total": onetime_total,
        "our_total_cost": our_total_cost,
        "ads_total_cost": ads_total_cost,
        "comparison_period": comparison_period,
    })


def _generate_fallback_analysis(lead) -> dict:
    pain_points = []
    category = (lead.product_interest or "bisnis").lower()

    if lead.rating and lead.rating < 4:
        pain_points.append(f"Rating Google Maps {lead.business_name} saat ini hanya {lead.rating}/5 — calon pelanggan cenderung skip bisnis dengan rating di bawah 4.0 dan langsung pilih kompetitor.")
    elif not lead.rating or lead.rating == 0:
        pain_points.append(f"{lead.business_name} belum memiliki rating yang cukup di Google Maps — ini membuat calon pelanggan ragu dan memilih kompetitor yang sudah punya banyak review positif.")

    pain_points.append(f"Saat calon pelanggan mencari '{category}' di Google, bisnis tanpa optimasi digital akan tenggelam di halaman belakang — artinya ratusan calon pelanggan potensial setiap bulan tidak pernah tahu {lead.business_name} ada.")

    city = ""
    if lead.address:
        city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else lead.address
    if city:
        pain_points.append(f"Kompetitor di area {city} yang sudah teroptimasi secara digital sedang mengambil pelanggan yang seharusnya milik Anda setiap harinya — dan gap ini semakin lebar setiap bulan yang berlalu.")
    else:
        pain_points.append("Tanpa kehadiran digital yang kuat, bisnis Anda kehilangan peluang dari pelanggan yang mencari layanan Anda secara online setiap hari.")

    return {
        "analysis": f"Berdasarkan audit digital yang kami lakukan terhadap {lead.business_name}, kami menemukan beberapa area kritis yang perlu segera ditangani untuk mencegah kehilangan pelanggan potensial ke kompetitor.",
        "pain_points": pain_points,
        "suggested_product": lead.product_interest or "SEO & Google Maps Optimization",
    }


def generate_report_for_lead(lead, db: Session, product_category: str = None) -> str:
    category = product_category or lead.product_interest or ""

    # Check existing report for same lead + same product category
    existing_reports = db.query(Proposal).filter(
        Proposal.lead_id == lead.id,
        Proposal.status == "Report",
    ).order_by(Proposal.created_at.desc()).all()
    for r in existing_reports:
        try:
            services = json.loads(r.services_detail) if r.services_detail else []
            report_products = " ".join(s.get("name", "") for s in services).lower()
            if category.lower() in report_products:
                return r.slug
        except Exception:
            pass
    # If no category match but has existing report and no specific category requested
    if existing_reports and not product_category:
        return existing_reports[0].slug

    # Use existing AI analysis if available, otherwise fallback
    existing_analysis = db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead.id).order_by(LeadAnalysis.id.desc()).first()
    if existing_analysis:
        analysis = existing_analysis
    else:
        fallback = _generate_fallback_analysis(lead)
        analysis = LeadAnalysis(
            lead_id=lead.id,
            analysis=fallback["analysis"],
            pain_points=json.dumps(fallback["pain_points"]),
            suggested_product=fallback["suggested_product"],
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(analysis)
        db.commit()

    # Pick products matching category
    products = db.query(Product).filter(Product.is_active == True).all()
    cat_lower = category.lower()
    matched_products = [p for p in products if cat_lower and cat_lower in (p.name or "").lower()] if cat_lower else []
    if not matched_products:
        matched_products = products[:3] if products else []
    services = [{"name": p.name, "price": p.base_price, "features": (p.description or "").split("\n")} for p in matched_products[:3]] if matched_products else [{"name": "SEO & Google Maps", "price": 0, "features": ["Optimasi ranking Google", "Setup Google Business Profile"]}]

    slug = generate_unique_slug(db, lead.business_name)
    report = Proposal(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        services_detail=json.dumps(services),
        total_price=sum(s["price"] for s in services),
        base_price=sum(s["price"] for s in services),
        discount_price=round(sum(s["price"] for s in services) * 0.85),
        discount_expires_at=None,
        additional_options=None,
        status="Report",
        created_at=datetime.now(timezone.utc).isoformat(),
        slug=slug,
        faqs=json.dumps([
            {"question": "Apakah audit ini gratis?", "answer": "Ya, audit digital ini 100% gratis dan tanpa kewajiban apapun. Kami ingin Anda melihat sendiri peluang yang selama ini terlewat."},
            {"question": "Berapa lama sampai terlihat hasilnya?", "answer": "Dengan optimasi yang tepat, peningkatan visibilitas di Google bisa terlihat dalam 14-30 hari kerja pertama."},
            {"question": "Apa bedanya dengan jasa SEO lain?", "answer": "Kami fokus pada hasil terukur — ranking naik, telepon masuk bertambah, dan pelanggan baru datang. Bukan sekadar laporan teknis yang membingungkan."},
        ]),
        selected_addons=_build_addons_from_products(db),
        timeline_data=None,
    )
    db.add(report)
    db.commit()
    return slug


def log_outreach_cost(db: Session, campaign_id: str, messages_count: int):
    provider = db.query(ProviderConfig).filter_by(id="FONNTE").first()
    if not provider:
        return
    cost = provider.price_per_unit_idr * messages_count
    provider.remaining_quota = max(0, (provider.remaining_quota or 0) - messages_count)
    campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
    if campaign:
        campaign.total_operational_cost_idr = (campaign.total_operational_cost_idr or 0) + cost
    db.commit()


def log_ai_cost(db: Session, campaign_id: str | None, model_name: str, input_tokens: int, output_tokens: int):
    provider_map = {"gemini": "GEMINI", "claude": "CLAUDE", "openai": "OPENAI"}
    provider_id = provider_map.get(model_name, model_name.upper())
    provider = db.query(ProviderConfig).filter_by(id=provider_id).first()
    if not provider:
        return
    cost_usd = (provider.price_input_token_usd * input_tokens / 1000) + (provider.price_output_token_usd * output_tokens / 1000)
    cost_idr = cost_usd * USD_TO_IDR
    provider.remaining_quota = (provider.remaining_quota or 0) + cost_idr
    if campaign_id:
        campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
        if campaign:
            campaign.total_operational_cost_idr = (campaign.total_operational_cost_idr or 0) + cost_idr
    db.commit()

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
    return user


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    email: str


class Business(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    whatsapp_url: Optional[str] = None
    google_rating: Optional[float] = None
    review_count: Optional[int] = None
    website_url: Optional[str] = None


class LeadOut(BaseModel):
    id: int
    business_name: str
    phone_number: str
    address: Optional[str]
    original_url: Optional[str]
    status: str
    product_interest: Optional[str]
    batch_name: Optional[str]
    rating: int = 0
    is_archived: bool = False
    deleted_at: Optional[str] = None
    lead_score: int = 0
    is_ghost_viewer: bool = False
    google_rating: Optional[float] = None
    review_count: Optional[int] = None
    website_url: Optional[str] = None
    model_config = {"from_attributes": True}


class ContactOut(BaseModel):
    id: int
    business_name: str
    owner_name: Optional[str]
    phone_number: str
    purchased_product: Optional[str]
    notes: Optional[str]
    model_config = {"from_attributes": True}


class ContactUpdate(BaseModel):
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    owner_name: Optional[str] = None
    purchased_product: Optional[str] = None
    notes: Optional[str] = None


class TemplateIn(BaseModel):
    product_category: str
    variant_name: str
    content: str


class TemplateOut(BaseModel):
    id: int
    product_category: str
    variant_name: str
    content: str
    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: str


class ProductUpdate(BaseModel):
    product_interest: str


class BlastIn(BaseModel):
    batch_name: str
    product_category: str
    min_rating: int = 0
    template_id: Optional[str] = None


class RatingUpdate(BaseModel):
    rating: int


class SettingsUpdate(BaseModel):
    fonnte_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_model: Optional[str] = None
    google_api_key: Optional[str] = None
    google_calendar_id: Optional[str] = None
    google_service_account_json: Optional[str] = None
    admin_wa: Optional[str] = None
    followup_enabled: Optional[str] = None
    followup_hour: Optional[str] = None
    cms_url: Optional[str] = None
    cms_api_token: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class ServiceDetail(BaseModel):
    name: str
    price: float
    features: List[str]


class TimelineItem(BaseModel):
    sequence: int
    title: str
    description: str


class ProposalIn(BaseModel):
    lead_id: int
    services: List[ServiceDetail]
    additional_options: Optional[str] = None
    timeline_data: Optional[List[TimelineItem]] = None
    source: Optional[str] = None
    roi_data: Optional[dict] = None


class ProposalOut(BaseModel):
    id: str
    lead_id: int
    services_detail: List[ServiceDetail]
    total_price: float
    additional_options: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    slug: Optional[str] = None
    timeline_data: Optional[List[TimelineItem]] = None
    roi_data: Optional[dict] = None
    model_config = {"from_attributes": True}


class ServiceItemIn(BaseModel):
    name: str
    default_price: float
    default_features: List[str]


class ServiceItemOut(BaseModel):
    id: str
    name: str
    default_price: float
    default_features: List[str]
    model_config = {"from_attributes": True}


class TrackOpenIn(BaseModel):
    proposal_id: str


class TrackPingIn(BaseModel):
    analytics_id: str
    seconds: int = 5
    sections_viewed: List[str] = []


class AnalyticsOut(BaseModel):
    id: str
    proposal_id: str
    opened_at: str
    last_ping: Optional[str] = None
    total_time_seconds: int
    sections_viewed: List[str]
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Finance Pydantic Schemas
# ---------------------------------------------------------------------------

class WalletIn(BaseModel):
    name: str
    balance: float = 0
    icon: Optional[str] = None
    color: Optional[str] = None


# ---------------------------------------------------------------------------
# Master Data Pydantic Schemas
# ---------------------------------------------------------------------------

class CategoryIn(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class CategoryOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    model_config = {"from_attributes": True}


class ProductIn(BaseModel):
    name: str
    description: Optional[str] = None
    base_price: float
    features: List[str] = []
    category_id: Optional[str] = None
    is_active: bool = True
    is_retainer: bool = False


class ProductOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    base_price: float
    features: List[str]
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    is_active: bool
    is_retainer: bool = False
    model_config = {"from_attributes": True}


class DynamicTemplateIn(BaseModel):
    name: str
    type: str
    content: str
    is_active: bool = True
    category_id: Optional[str] = None


class DynamicTemplateOut(BaseModel):
    id: str
    name: str
    type: str
    content: str
    is_active: bool
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    model_config = {"from_attributes": True}


class WalletOut(BaseModel):
    id: int
    name: str
    balance: float
    icon: Optional[str] = None
    color: Optional[str] = None
    model_config = {"from_attributes": True}


class TransactionIn(BaseModel):
    wallet_id: int
    type: str  # income / expense
    amount: float
    category: Optional[str] = None
    date: str
    notes: Optional[str] = None
    lead_id: Optional[int] = None
    is_billed: bool = False


class TransactionOut(BaseModel):
    id: int
    wallet_id: int
    type: str
    amount: float
    category: Optional[str] = None
    date: str
    notes: Optional[str] = None
    lead_id: Optional[int] = None
    is_billed: bool
    lead_name: Optional[str] = None
    model_config = {"from_attributes": True}


class SubscriptionIn(BaseModel):
    wallet_id: int
    name: str
    amount: float
    billing_cycle: str = "monthly"
    next_billing_date: str
    is_active: bool = True


class SubscriptionOut(BaseModel):
    id: int
    wallet_id: int
    name: str
    amount: float
    billing_cycle: str
    next_billing_date: str
    is_active: bool
    wallet_name: Optional[str] = None
    model_config = {"from_attributes": True}


class FinanceReportOut(BaseModel):
    total_balance: float
    break_even_point: float
    financial_runway_months: float
    expense_by_category: List[dict]


# ---------------------------------------------------------------------------
# Project & ClientNote Pydantic Schemas
# ---------------------------------------------------------------------------

class ProjectIn(BaseModel):
    lead_id: Optional[int] = None
    name: str
    type: str  # FIXED / RETAINER
    status: str = "ACTIVE"
    nominal: float = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    color: Optional[str] = "yellow"


class ProjectOut(BaseModel):
    id: str
    lead_id: Optional[int] = None
    name: str
    type: str
    status: str
    nominal: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    color: Optional[str] = "yellow"
    is_archived: bool = False
    model_config = {"from_attributes": True}


class ClientNoteIn(BaseModel):
    lead_id: int
    category: str  # BISNIS / TEKNIS / PENTING
    content: str


class ClientNoteOut(BaseModel):
    id: str
    lead_id: int
    timestamp: str
    actor: str
    category: str
    content: str
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Board Pydantic Schemas (Trello-like)
# ---------------------------------------------------------------------------

class LeadMin(BaseModel):
    id: int
    business_name: str
    model_config = {"from_attributes": True}


class BoardCardCommentOut(BaseModel):
    id: str
    card_id: str
    author: str
    content: str
    created_at: str
    model_config = {"from_attributes": True}


class BoardCardChecklistOut(BaseModel):
    id: str
    card_id: str
    text: str
    is_done: bool
    position: int
    model_config = {"from_attributes": True}


class BoardCardActivityOut(BaseModel):
    id: str
    card_id: str
    action: str
    description: str
    actor: str
    created_at: str
    model_config = {"from_attributes": True}


class BoardCardOut(BaseModel):
    id: str
    column_id: str
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[list[str]] = []
    position: int
    is_archived: bool
    created_at: str
    updated_at: Optional[str] = None
    lead_id: Optional[int] = None
    lead: Optional[LeadMin] = None
    color: Optional[str] = "yellow"
    comments: list[BoardCardCommentOut] = []
    checklist: list[BoardCardChecklistOut] = []
    activity: list[BoardCardActivityOut] = []
    model_config = {"from_attributes": True}


class BoardColumnOut(BaseModel):
    id: str
    board_id: str
    name: str
    position: int
    color: Optional[str] = "yellow"
    cards: list[BoardCardOut] = []
    model_config = {"from_attributes": True}


class BoardOut(BaseModel):
    id: str
    project_id: str
    created_at: str
    color: Optional[str] = "yellow"
    columns: list[BoardColumnOut] = []
    model_config = {"from_attributes": True}


class BoardColumnIn(BaseModel):
    name: str
    position: Optional[int] = None
    color: Optional[str] = "yellow"


class BoardCardIn(BaseModel):
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[list[str]] = []
    lead_id: Optional[int] = None
    color: Optional[str] = "yellow"


class BoardCardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[list[str]] = None
    column_id: Optional[str] = None
    position: Optional[int] = None
    is_archived: Optional[bool] = None
    lead_id: Optional[int] = None
    color: Optional[str] = None


class MoveCardRequest(BaseModel):
    column_id: str
    position: Optional[int] = None


class BoardCardCommentIn(BaseModel):
    content: str


class BoardCardChecklistIn(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Credentials & Documents Pydantic Schemas
# ---------------------------------------------------------------------------

class CredentialFieldIn(BaseModel):
    key: str
    value: str
    is_secret: bool = False


class CredentialIn(BaseModel):
    lead_id: Optional[int] = None
    category: str
    title: str
    fields: list[CredentialFieldIn]


class CredentialFieldOut(BaseModel):
    key: str
    value: str
    is_secret: bool = False


class CredentialOut(BaseModel):
    id: str
    lead_id: Optional[int] = None
    category: str
    title: str
    fields: list[CredentialFieldOut]
    created_at: str
    model_config = {"from_attributes": True}


class CredentialUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    fields: Optional[list[CredentialFieldIn]] = None


class DocumentIn(BaseModel):
    lead_id: Optional[int] = None
    title: str
    cloud_url: str


class DocumentOut(BaseModel):
    id: str
    lead_id: Optional[int] = None
    title: str
    cloud_url: str
    created_at: str
    model_config = {"from_attributes": True}


VALID_STATUSES = {"Scraped", "Contacted", "Replied", "Closed", "Closed/Client"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_phone(raw: str) -> Optional[str]:
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif not digits.startswith("62"):
        digits = "62" + digits
    return digits


def make_wa_url(phone_digits: str) -> str:
    return f"https://wa.me/{phone_digits}"


def calculate_lead_score(has_website: bool, google_rating: Optional[float], user_ratings_total: Optional[int], has_phone: bool) -> int:
    points = 0
    if not has_website:
        points += 3
    if google_rating is None or google_rating < 4.0:
        points += 2
    if user_ratings_total is None or user_ratings_total < 10:
        points += 2
    if has_phone:
        points += 3
    points = min(points, 10)
    if points >= 8:
        return 5
    elif points >= 6:
        return 4
    elif points >= 4:
        return 3
    elif points >= 2:
        return 2
    return 1


def generate_batch_name(category: str, location: str) -> str:
    date_str = datetime.now().strftime("%d %b %Y")
    parts = [p for p in [category.strip(), location.strip()] if p]
    label = " - ".join(parts) if parts else "Scrape"
    return f"{label} · {date_str}"


def get_fonnte_token(db: Session) -> str:
    row = db.query(SystemSettings).filter_by(key="fonnte_token").first()
    return (row.value or "") if row else ""


async def send_fonnte_message(phone: str, message: str, token: str) -> bool:
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": token},
                data={"target": phone, "message": message, "delay": "5"},
            )
            return resp.status_code == 200
    except Exception:
        return False


def _send_fonnte_sync(phone: str, message: str, token: str, _httpx) -> bool:
    if not token:
        return False
    try:
        with _httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": token},
                data={"target": phone, "message": message, "delay": "5"},
            )
            return resp.status_code == 200 and resp.json().get("status") != False
    except Exception as e:
        print(f"[FONNTE ERROR] {e}", flush=True)
        return False


def run_blast_sync(batch_name: str, product_category: str, min_rating: int, db_url: str, jwt_secret: str, template_id: str = None):
    import httpx as _httpx
    import time as _time
    from sqlalchemy import create_engine as ce
    from sqlalchemy.orm import sessionmaker as sm
    _ca = {"check_same_thread": False} if "sqlite" in db_url else {}
    _engine = ce(db_url, connect_args=_ca, pool_recycle=60, pool_pre_ping=True, pool_size=1, max_overflow=0)
    _Session = sm(bind=_engine)
    db = _Session()
    try:
        token = get_fonnte_token(db)
        query = db.query(Lead).filter(
            Lead.batch_name == batch_name,
            Lead.status == "Scraped",
        )
        if min_rating > 0:
            query = query.filter(Lead.rating >= min_rating)
        leads = query.all()

        _blast_jobs[batch_name] = {"status": "running", "total": len(leads), "sent": 0, "failed": 0, "batch_name": batch_name}

        dynamic_templates = []
        if template_id:
            specific = db.query(DynamicTemplate).filter(DynamicTemplate.id == template_id).first()
            if specific:
                dynamic_templates = [specific]
        else:
            dynamic_templates = db.query(DynamicTemplate).filter(
                DynamicTemplate.type == "WA_BLAST",
                DynamicTemplate.is_active == True,
            ).all()

        old_templates = []
        if not dynamic_templates:
            old_templates = db.query(MessageTemplate).filter(
                MessageTemplate.product_category == product_category
            ).all()
            if not old_templates:
                old_templates = db.query(MessageTemplate).filter(
                    MessageTemplate.product_category == "Lainnya"
                ).all()

        db.close()

        for lead in leads:
            db = _Session()
            # Auto-analyze with AI if not yet analyzed
            existing_analysis = db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead.id).first()
            if not existing_analysis:
                try:
                    _products = db.query(Product).filter(Product.is_active == True).all()
                    _product_list = "\n".join([f"- {p.name}: {p.description or ''}" for p in _products]) if _products else "- SEO\n- Web Development"
                    _config = get_ai_config(db)
                    prompt = build_analysis_prompt(lead, _product_list)
                    db.close()
                    text = _call_ai_sync(prompt, _config, _httpx)
                    parsed = parse_ai_response(text)
                    db = _Session()
                    db.add(LeadAnalysis(
                        lead_id=lead.id,
                        analysis=text,
                        pain_points=json.dumps(parsed.get("pain_points", [])),
                        suggested_product=parsed.get("suggested_product", ""),
                        analyzed_at=datetime.now(timezone.utc).isoformat(),
                    ))
                    db.commit()
                    print(f"[BLAST] AI analyzed lead={lead.id} {lead.business_name}", flush=True)
                except Exception as e:
                    print(f"[BLAST] AI analyze failed lead={lead.id}: {e}", flush=True)
                    try:
                        db.close()
                    except Exception:
                        pass
                    db = _Session()

            frontend_url = _get_setting("frontend_url", os.environ["FRONTEND_URL"])
            report_slug = generate_report_for_lead(lead, db)
            report_link = f"{FRONTEND_URL}/r/{report_slug}"

            if dynamic_templates:
                tmpl = random.choice(dynamic_templates)
                message = tmpl.content.replace("{{client_name}}", lead.business_name).replace("{{business_name}}", lead.business_name).replace("{{product_name}}", product_category)
                message = message.replace("{{proposal_link}}", f"\n{report_link}\n")
            elif old_templates:
                tmpl = random.choice(old_templates)
                message = tmpl.content.replace("{{business_name}}", lead.business_name)
                message = message.replace("{{proposal_link}}", f"\n{report_link}\n")
            else:
                message = f"Halo {lead.business_name}, kami dari Kantor Teman ingin menawarkan layanan {product_category}. Apakah ada waktu untuk berdiskusi?\n\nLihat laporan audit digital Anda di sini:\n{report_link}"

            success = _send_fonnte_sync(lead.phone_number, message, token, _httpx)
            if success:
                lead.status = "Contacted"
                db.commit()
                _blast_jobs[batch_name]["sent"] += 1
            else:
                _blast_jobs[batch_name]["failed"] += 1
            db.close()
            _time.sleep(5)

        _blast_jobs[batch_name]["status"] = "done"
        print(f"[BLAST DONE] sent={_blast_jobs[batch_name]['sent']}/{len(leads)}", flush=True)
    except Exception as e:
        import traceback
        print(f"[BLAST ERROR] {e}", flush=True)
        traceback.print_exc()
        _blast_jobs[batch_name]["status"] = "error"
        _blast_jobs[batch_name]["error"] = str(e)
    finally:
        try:
            db.close()
        except Exception:
            pass
        _engine.dispose()


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    return TokenOut(
        access_token=create_token(user.id, user.email),
        name=user.name,
        email=user.email,
    )


# ---------------------------------------------------------------------------
# User / Settings endpoints
# ---------------------------------------------------------------------------

@app.get("/api/user/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "name": current_user.name, "email": current_user.email}


@app.put("/api/user/me")
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


@app.get("/api/settings")
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = ["fonnte_token", "gemini_api_key", "claude_api_key", "openai_api_key", "ai_provider", "ai_base_url", "ai_model", "google_api_key", "google_calendar_id", "google_service_account_json", "admin_wa", "followup_enabled", "followup_hour", "cms_url", "cms_api_token"]
    result = {}
    for k in keys:
        row = db.query(SystemSettings).filter_by(key=k).first()
        result[k] = row.value if row else ""
    if not result["ai_provider"]:
        result["ai_provider"] = "gemini"
    return result


@app.put("/api/settings")
def update_settings(body: SettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings_map = {
        "fonnte_token": body.fonnte_token,
        "gemini_api_key": body.gemini_api_key,
        "claude_api_key": body.claude_api_key,
        "openai_api_key": body.openai_api_key,
        "ai_provider": body.ai_provider,
        "ai_base_url": body.ai_base_url,
        "ai_model": body.ai_model,
        "google_api_key": body.google_api_key,
        "google_calendar_id": body.google_calendar_id,
        "google_service_account_json": body.google_service_account_json,
        "admin_wa": body.admin_wa,
        "followup_enabled": body.followup_enabled,
        "followup_hour": body.followup_hour,
        "cms_url": body.cms_url,
        "cms_api_token": body.cms_api_token,
    }
    for key, value in settings_map.items():
        if value is not None:
            row = db.query(SystemSettings).filter_by(key=key).first()
            if row:
                row.value = value
            else:
                db.add(SystemSettings(key=key, value=value))
    db.commit()
    return {"ok": True}


@app.post("/api/admin/seed")
def run_seed_endpoint(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Run seeder via HTTP — use once after first deploy."""
    from seed import categories, products_data, templates_data
    import uuid as _uuid

    db.query(Product).delete()
    db.query(Category).delete()
    db.query(DynamicTemplate).filter(DynamicTemplate.type.in_(["WA_BLAST", "FOLLOW_UP"])).delete()
    db.commit()

    cat_objects = {}
    for key, cat in categories.items():
        c = Category(id=str(_uuid.uuid4()), name=cat["name"], description=cat["description"], is_active=True)
        db.add(c)
        cat_objects[key] = c
    db.commit()

    for name, desc, price, features, cat_key, is_retainer in products_data:
        db.add(Product(
            id=str(_uuid.uuid4()), name=name, description=desc, base_price=price,
            features=json.dumps(features), category_id=cat_objects[cat_key].id,
            is_active=True, is_retainer=is_retainer,
        ))
    db.commit()

    for name, ttype, cat_key, content in templates_data:
        db.add(DynamicTemplate(
            id=str(_uuid.uuid4()), name=name, type=ttype, content=content,
            is_active=True, category_id=cat_objects[cat_key].id,
        ))
    db.commit()

    seed_data(db)
    return {"ok": True, "message": "Seed berhasil: categories, products, templates"}


@app.post("/api/settings/test-api")
async def test_api_connection(
    provider: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test apakah API key yang disimpan bisa terhubung dengan benar."""
    config = get_ai_config(db)

    if provider == "fonnte":
        token = get_fonnte_token(db)
        if not token:
            return {"success": False, "message": "Token Fonnte belum diisi."}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.fonnte.com/validate",
                    headers={"Authorization": token},
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Fonnte terhubung."}
                return {"success": False, "message": f"Fonnte error: {resp.status_code} - {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"Gagal koneksi ke Fonnte: {str(e)}"}

    elif provider == "gemini":
        if not config["gemini_key"]:
            return {"success": False, "message": "Gemini API Key belum diisi."}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={config['gemini_key']}",
                    json={"contents": [{"parts": [{"text": "Balas dengan satu kata: OK"}]}]},
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Gemini API terhubung."}
                return {"success": False, "message": f"Gemini error: {resp.status_code} - {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"Gagal koneksi ke Gemini: {str(e)}"}

    elif provider == "claude":
        if not config["claude_key"]:
            return {"success": False, "message": "Claude API Key belum diisi."}
        base_url = config.get("base_url") or "https://api.openai.com/v1"
        model = config.get("model") or "claude-haiku-4-5-20251001"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config['claude_key']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Balas dengan satu kata: OK"}],
                    },
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Claude API terhubung."}
                return {"success": False, "message": f"Claude error: {resp.status_code} - {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"Gagal koneksi ke Claude: {str(e)}"}

    elif provider == "openai":
        if not config["openai_key"]:
            return {"success": False, "message": "OpenAI API Key belum diisi."}
        base_url = config.get("base_url") or "https://api.openai.com/v1"
        model = config.get("model") or "gpt-4o-mini"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config['openai_key']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "Balas dengan satu kata: OK"}],
                        "max_tokens": 10,
                    },
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "OpenAI API terhubung."}
                return {"success": False, "message": f"OpenAI error: {resp.status_code} - {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": f"Gagal koneksi ke OpenAI: {str(e)}"}

    return {"success": False, "message": f"Provider '{provider}' tidak dikenal."}


# ---------------------------------------------------------------------------
# Search / Scrape
# ---------------------------------------------------------------------------

@app.get("/api/search", response_model=list[Business])
async def search_businesses(
    q: str = Query(...),
    max_results: int = Query(20, ge=1, le=60),
    product_interest: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    async with search_semaphore:
        api_key = _get_setting("google_api_key", GOOGLE_API_KEY or "")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not configured")

        batch = generate_batch_name(category or "", location or "")
        results: list[Business] = []
        page_token: Optional[str] = None

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.internationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.location,nextPageToken",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            while len(results) < max_results:
                body: dict = {"textQuery": q, "pageSize": min(20, max_results - len(results)), "languageCode": "id"}
                if page_token:
                    body["pageToken"] = page_token

                resp = await client.post(PLACES_NEW_SEARCH_URL, json=body, headers=headers)
                if resp.status_code != 200:
                    detail = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
                    raise HTTPException(status_code=502, detail=f"Google API error: {detail}")

                data = resp.json()
                for place in data.get("places", []):
                    if len(results) >= max_results:
                        break
                    raw_phone = place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber")
                    phone_digits = normalize_phone(raw_phone) if raw_phone else None
                    wa_url = make_wa_url(phone_digits) if phone_digits else None
                    address = place.get("formattedAddress", "")
                    name = place.get("displayName", {}).get("text", "")
                    website = place.get("websiteUri")
                    google_rating = place.get("rating")
                    user_ratings_total = place.get("userRatingCount")
                    location_data = place.get("location", {})
                    latitude = location_data.get("latitude") if location_data else None
                    longitude = location_data.get("longitude") if location_data else None
                    if phone_digits and not db.query(Lead).filter(Lead.phone_number == phone_digits).first():
                        score = calculate_lead_score(
                            has_website=bool(website),
                            google_rating=google_rating,
                            user_ratings_total=user_ratings_total,
                            has_phone=True,
                        )
                        db.add(Lead(business_name=name, phone_number=phone_digits, address=address,
                                    original_url=wa_url, product_interest=product_interest, batch_name=batch,
                                    rating=score, website_url=website, google_rating=google_rating,
                                    review_count=user_ratings_total, latitude=latitude, longitude=longitude))
                        db.commit()
                    results.append(Business(name=name, address=address, phone=raw_phone, whatsapp_url=wa_url,
                                            google_rating=google_rating, review_count=user_ratings_total, website_url=website))

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        # Record scrape history
        db.add(ScrapeHistory(
            category=category or q,
            location=location or "",
            product_interest=product_interest,
            results_count=len(results),
            scraped_at=datetime.now(timezone.utc).isoformat(),
        ))
        db.commit()

        return results


@app.get("/api/scrape-history")
def get_scrape_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = db.query(ScrapeHistory).order_by(ScrapeHistory.id.desc()).limit(50).all()
    return [{
        "id": h.id,
        "category": h.category,
        "location": h.location,
        "product_interest": h.product_interest,
        "results_count": h.results_count,
        "scraped_at": h.scraped_at,
    } for h in history]


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

@app.get("/api/leads")
def get_leads(
    status: Optional[str] = Query(None),
    batch_name: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    archived_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Lead)
    if archived_only:
        query = query.filter(Lead.is_archived == True)
    elif not include_archived:
        query = query.filter(Lead.is_archived == False)
    if status:
        query = query.filter(Lead.status == status)
    if batch_name:
        query = query.filter(Lead.batch_name == batch_name)
    leads = query.order_by(Lead.lead_score.desc()).all()

    # Ghost Viewer aggregation: count LINK_CLICKED in last 48h
    threshold_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    ghost_lead_ids = set()
    if leads:
        lead_ids = [l.id for l in leads]
        ghost_rows = db.query(
            LeadActivityLog.lead_id, func.count(LeadActivityLog.id).label("click_count")
        ).filter(
            LeadActivityLog.lead_id.in_(lead_ids),
            LeadActivityLog.activity_type == "LINK_CLICKED",
            LeadActivityLog.created_at >= threshold_48h,
        ).group_by(LeadActivityLog.lead_id).having(func.count(LeadActivityLog.id) >= 5).all()
        ghost_lead_ids = {row[0] for row in ghost_rows}

    results = []
    for lead in leads:
        lead_dict = {
            "id": lead.id,
            "business_name": lead.business_name,
            "phone_number": lead.phone_number,
            "address": lead.address,
            "original_url": lead.original_url,
            "status": lead.status,
            "product_interest": lead.product_interest,
            "batch_name": lead.batch_name,
            "rating": lead.rating or 0,
            "is_archived": lead.is_archived,
            "deleted_at": lead.deleted_at,
            "lead_score": lead.lead_score or 0,
            "is_ghost_viewer": lead.id in ghost_lead_ids,
            "google_rating": lead.google_rating,
            "review_count": lead.review_count,
            "website_url": lead.website_url,
        }
        results.append(lead_dict)
    return results


@app.get("/api/leads/map")
def get_leads_map(
    status: Optional[str] = Query(None),
    batch_name: Optional[str] = Query(None),
    product_interest: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Lead).filter(Lead.latitude.isnot(None), Lead.longitude.isnot(None), Lead.is_archived == False)
    if status:
        query = query.filter(Lead.status == status)
    if batch_name:
        query = query.filter(Lead.batch_name == batch_name)
    if product_interest:
        query = query.filter(Lead.product_interest == product_interest)
    leads = query.all()
    return [{
        "id": lead.id,
        "business_name": lead.business_name,
        "phone_number": lead.phone_number,
        "address": lead.address,
        "status": lead.status,
        "product_interest": lead.product_interest,
        "batch_name": lead.batch_name,
        "website_url": lead.website_url,
        "google_rating": lead.google_rating,
        "review_count": lead.review_count,
        "latitude": lead.latitude,
        "longitude": lead.longitude,
        "lead_score": lead.lead_score or 0,
    } for lead in leads]


class LeadCreate(BaseModel):
    business_name: str
    phone_number: str
    address: Optional[str] = None
    product_interest: Optional[str] = None
    batch_name: Optional[str] = None


class LeadEdit(BaseModel):
    business_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    product_interest: Optional[str] = None
    batch_name: Optional[str] = None


@app.post("/api/leads", response_model=LeadOut, status_code=201)
def create_lead_manual(body: LeadCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Lead).filter(Lead.phone_number == body.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Nomor {body.phone_number} sudah ada di database ({existing.business_name}).")
    lead = Lead(
        business_name=body.business_name,
        phone_number=body.phone_number,
        address=body.address,
        product_interest=body.product_interest,
        batch_name=body.batch_name or "Manual",
        status="Scraped",
        rating=0,
        lead_score=0,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    log_audit(db, current_user.name, "CREATE", "leads", lead.id, {"source": "manual"})
    return lead


class WaSendIn(BaseModel):
    lead_id: int
    message: str


@app.post("/api/wa/send")
def send_wa_manual(body: WaSendIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    print(f"[WA SEND] lead_id={body.lead_id}", flush=True)
    lead = db.query(Lead).filter(Lead.id == body.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    token = get_fonnte_token(db)
    print(f"[WA SEND] phone={lead.phone_number} token={token[:10] if token else 'EMPTY'}...", flush=True)
    if not token:
        raise HTTPException(status_code=400, detail="Fonnte token belum dikonfigurasi.")
    import httpx as _httpx
    success = _send_fonnte_sync(lead.phone_number, body.message, token, _httpx)
    print(f"[WA SEND] success={success}", flush=True)
    if success:
        if lead.status == "Scraped":
            lead.status = "Contacted"
            db.commit()
        log_outreach_cost(db, None, 1)
        log_audit(db, current_user.name, "SEND_WA", "leads", lead.id, {"type": "manual"})
        return {"success": True, "message": "Pesan terkirim via Fonnte."}
    raise HTTPException(status_code=502, detail="Gagal mengirim pesan via Fonnte.")


@app.put("/api/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, body: LeadEdit, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    changes = {}
    if body.business_name is not None:
        changes["business_name"] = {"old": lead.business_name, "new": body.business_name}
        lead.business_name = body.business_name
    if body.phone_number is not None:
        changes["phone_number"] = {"old": lead.phone_number, "new": body.phone_number}
        lead.phone_number = body.phone_number
    if body.address is not None:
        changes["address"] = {"old": lead.address, "new": body.address}
        lead.address = body.address
    if body.product_interest is not None:
        changes["product_interest"] = {"old": lead.product_interest, "new": body.product_interest}
        lead.product_interest = body.product_interest
    if body.batch_name is not None:
        changes["batch_name"] = {"old": lead.batch_name, "new": body.batch_name}
        lead.batch_name = body.batch_name
    db.commit()
    db.refresh(lead)
    if changes:
        log_audit(db, current_user.name, "UPDATE", "leads", lead_id, changes)
    return lead


@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    db.query(Proposal).filter(Proposal.lead_id == lead_id).delete()
    db.query(LeadActivityLog).filter(LeadActivityLog.lead_id == lead_id).delete()
    db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead_id).delete()
    db.query(Project).filter(Project.lead_id == lead_id).delete()
    db.query(ClientNote).filter(ClientNote.lead_id == lead_id).delete()
    db.query(FollowUpSequence).filter(FollowUpSequence.lead_id == lead_id).delete()
    db.query(ReengagementAlert).filter(ReengagementAlert.lead_id == lead_id).delete()
    db.query(ClientCredential).filter(ClientCredential.lead_id == lead_id).delete()
    db.query(ClientDocument).filter(ClientDocument.lead_id == lead_id).delete()
    db.delete(lead)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "leads", lead_id, {"business_name": lead.business_name})
    return {"detail": "Lead berhasil dihapus"}


@app.get("/api/leads/batches")
def get_batches(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Lead.batch_name).where(Lead.batch_name.isnot(None)).distinct()).scalars().all()
    return [r for r in rows if r]


@app.patch("/api/leads/{lead_id}/status", response_model=LeadOut)
def update_lead_status(lead_id: int, body: StatusUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Status tidak valid.")
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    old_status = lead.status
    lead.status = body.status
    db.commit()
    db.refresh(lead)
    log_audit(db, current_user.name, "UPDATE", "leads", lead_id, {"field": "status", "old": old_status, "new": body.status})
    return lead


@app.patch("/api/leads/{lead_id}/product", response_model=LeadOut)
def update_lead_product(lead_id: int, body: ProductUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    lead.product_interest = body.product_interest
    db.commit()
    db.refresh(lead)
    return lead


@app.patch("/api/leads/{lead_id}/rating", response_model=LeadOut)
def update_lead_rating(lead_id: int, body: RatingUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=400, detail="Rating harus antara 1-5")
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    lead.rating = body.rating
    db.commit()
    db.refresh(lead)
    return lead


@app.post("/api/leads/{lead_id}/convert", response_model=ContactOut)
def convert_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    existing = db.query(Contact).filter(Contact.phone_number == lead.phone_number).first()
    if existing:
        lead.status = "Closed/Client"
        db.commit()
        return existing
    contact = Contact(business_name=lead.business_name, phone_number=lead.phone_number, purchased_product=lead.product_interest)
    db.add(contact)
    lead.status = "Closed/Client"
    db.commit()
    db.refresh(contact)
    return contact




@app.post("/api/leads/restore/{lead_id}", response_model=LeadOut)
def restore_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    lead.is_archived = False
    lead.deleted_at = None
    db.commit()
    db.refresh(lead)
    log_audit(db, current_user.name, "RESTORE", "leads", lead_id, {"business_name": lead.business_name})
    return lead


@app.delete("/api/leads/batch/{batch_name}", status_code=204)
def delete_batch(batch_name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.batch_name == batch_name, Lead.is_archived == False).all()
    if not leads:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")
    for lead in leads:
        lead.is_archived = True
        lead.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    log_audit(db, current_user.name, "DELETE", "leads", batch_name, {"action": "batch_delete", "count": len(leads)})


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

@app.get("/api/contacts", response_model=list[ContactOut])
def get_contacts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Contact).all()


@app.post("/api/contacts", response_model=ContactOut, status_code=201)
def create_contact(body: ContactUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.business_name or not body.phone_number:
        raise HTTPException(status_code=400, detail="Nama bisnis dan nomor WA wajib diisi")
    existing = db.query(Contact).filter(Contact.phone_number == body.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nomor WA sudah terdaftar")
    contact = Contact(
        business_name=body.business_name,
        phone_number=body.phone_number,
        owner_name=body.owner_name,
        purchased_product=body.purchased_product,
        notes=body.notes,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    log_audit(db, current_user.name, "CREATE", "contacts", contact.id, {"business_name": body.business_name})
    return contact


@app.patch("/api/contacts/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, body: ContactUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Kontak tidak ditemukan")
    if body.owner_name is not None:
        contact.owner_name = body.owner_name
    if body.purchased_product is not None:
        contact.purchased_product = body.purchased_product
    if body.notes is not None:
        contact.notes = body.notes
    db.commit()
    db.refresh(contact)
    return contact


@app.delete("/api/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Kontak tidak ditemukan")
    db.delete(contact)
    db.commit()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

@app.get("/api/templates", response_model=list[TemplateOut])
def get_templates(product_category: Optional[str] = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(MessageTemplate)
    if product_category:
        query = query.filter(MessageTemplate.product_category == product_category)
    return query.all()


@app.post("/api/templates", response_model=TemplateOut, status_code=201)
def create_template(body: TemplateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tmpl = MessageTemplate(**body.model_dump())
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@app.patch("/api/templates/{tmpl_id}", response_model=TemplateOut)
def update_template(tmpl_id: int, body: TemplateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tmpl = db.query(MessageTemplate).filter(MessageTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    tmpl.product_category = body.product_category
    tmpl.variant_name = body.variant_name
    tmpl.content = body.content
    db.commit()
    db.refresh(tmpl)
    return tmpl


@app.delete("/api/templates/{tmpl_id}", status_code=204)
def delete_template(tmpl_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tmpl = db.query(MessageTemplate).filter(MessageTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    db.delete(tmpl)
    db.commit()


@app.get("/api/templates/random")
def get_random_template(
    product_category: str = Query(...),
    business_name: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates = db.query(MessageTemplate).filter(MessageTemplate.product_category == product_category).all()
    if not templates:
        templates = db.query(MessageTemplate).filter(MessageTemplate.product_category == "Lainnya").all()
    if not templates:
        return {"message": None}
    tmpl = random.choice(templates)
    return {"message": tmpl.content.replace("{{business_name}}", business_name), "variant_name": tmpl.variant_name, "template_id": tmpl.id}


# ---------------------------------------------------------------------------
# Campaign / Blast
# ---------------------------------------------------------------------------

@app.post("/api/campaign/blast")
async def start_blast(
    body: BlastIn,
    current_user: User = Depends(get_current_user),
):
    import threading
    threading.Thread(target=run_blast_sync, args=(body.batch_name, body.product_category, body.min_rating, DATABASE_URL, JWT_SECRET, body.template_id), daemon=True).start()
    return {"message": "Campaign berjalan di background!", "batch_name": body.batch_name}


# ---------------------------------------------------------------------------
# Public Template Endpoint (for proposal page)
# ---------------------------------------------------------------------------

@app.get("/api/public/proposal-templates")
def get_proposal_templates(db: Session = Depends(get_db)):
    intro = db.query(DynamicTemplate).filter(
        DynamicTemplate.type.in_(["PROPOSAL_INTRO", "PROPOSAL_TEXT"]),
        DynamicTemplate.is_active == True,
    ).first()
    outro = db.query(DynamicTemplate).filter(
        DynamicTemplate.type == "PROPOSAL_OUTRO",
        DynamicTemplate.is_active == True,
    ).first()
    return {
        "intro": intro.content if intro else None,
        "outro": outro.content if outro else None,
    }


# ---------------------------------------------------------------------------
# Proposals
# ---------------------------------------------------------------------------

def _proposal_to_out(proposal, lead) -> ProposalOut:
    timeline = None
    if proposal.timeline_data:
        timeline = sorted(json.loads(proposal.timeline_data), key=lambda x: x["sequence"])
    roi = None
    if proposal.roi_data:
        roi = json.loads(proposal.roi_data) if isinstance(proposal.roi_data, str) else proposal.roi_data
    return ProposalOut(
        id=proposal.id,
        lead_id=proposal.lead_id,
        services_detail=[ServiceDetail(**s) for s in json.loads(proposal.services_detail)],
        total_price=proposal.total_price,
        additional_options=proposal.additional_options,
        status=proposal.status,
        created_at=proposal.created_at,
        business_name=lead.business_name if lead else None,
        phone_number=lead.phone_number if lead else None,
        slug=proposal.slug,
        timeline_data=timeline,
        roi_data=roi,
    )


@app.post("/api/proposals", response_model=ProposalOut, status_code=201)
def create_proposal(body: ProposalIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = None
    if body.source == "contact":
        contact = db.query(Contact).filter(Contact.id == body.lead_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact tidak ditemukan")
        lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
        if not lead:
            lead = Lead(
                business_name=contact.business_name,
                phone_number=contact.phone_number,
                status="Closed/Client",
                product_interest=contact.purchased_product,
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
    else:
        lead = db.query(Lead).filter(Lead.id == body.lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    services_data = [s.model_dump() for s in body.services]
    total = sum(s.price for s in body.services)
    discount_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    default_faqs = json.dumps([
        {"question": "Apakah teknik SEO yang digunakan aman (White-Hat)?", "answer": "100% aman. Kami hanya menggunakan teknik White-Hat SEO yang sesuai pedoman resmi Google. Tidak ada risiko penalti atau banned untuk bisnis Anda."},
        {"question": "Berapa lama sampai peringkat Google Maps naik?", "answer": "Estimasi 14-30 hari kerja untuk mulai terlihat peningkatan signifikan di Google Maps, tergantung tingkat kompetisi di wilayah Anda."},
        {"question": "Kata kunci apa yang akan ditargetkan?", "answer": "Kami fokus pada kata kunci dengan Intent Membeli tinggi — yaitu kata kunci yang diketik oleh calon pelanggan yang sudah siap bertransaksi, bukan sekadar browsing."},
    ])

    # Timeline Data: use provided data or fallback to default template
    timeline_json = None
    if body.timeline_data and len(body.timeline_data) > 0:
        sorted_timeline = sorted([t.model_dump() for t in body.timeline_data], key=lambda x: x["sequence"])
        timeline_json = json.dumps(sorted_timeline)
    else:
        # Fallback: pick timeline template based on product interest keywords
        category = (lead.product_interest or "").lower()
        seo_keywords = ["seo", "google", "maps", "lokal", "local", "ranking", "peringkat"]
        web_keywords = ["web", "website", "landing", "development", "dev", "frontend", "fullstack"]
        template_id = None
        if any(kw in category for kw in seo_keywords):
            template_id = "timeline-seo-lokal"
        elif any(kw in category for kw in web_keywords):
            template_id = "timeline-web-dev"
        else:
            template_id = "timeline-seo-lokal"
        tmpl = db.query(DynamicTemplate).filter_by(id=template_id, type="TIMELINE_TEMPLATE", is_active=True).first()
        if tmpl:
            timeline_json = tmpl.content

    proposal = Proposal(
        id=str(uuid.uuid4()),
        lead_id=lead.id,
        services_detail=json.dumps(services_data),
        total_price=total,
        base_price=total,
        discount_price=round(total * 0.85),
        discount_expires_at=discount_expires,
        additional_options=body.additional_options,
        status="Sent",
        created_at=datetime.now(timezone.utc).isoformat(),
        slug=generate_unique_slug(db, lead.business_name),
        faqs=getattr(body, 'faqs', None) or default_faqs,
        selected_addons=_build_addons_from_products(db),
        timeline_data=timeline_json,
        roi_data=_build_roi_data(db, body.services, body.roi_data),
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    log_audit(db, current_user.name, "CREATE", "proposals", proposal.id, {"lead": lead.business_name, "total": total})
    return _proposal_to_out(proposal, lead)


@app.get("/api/proposals/public/{proposal_id}", response_model=ProposalOut)
def get_public_proposal(proposal_id: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    return _proposal_to_out(proposal, lead)


@app.get("/p/{slug}")
def redirect_proposal_by_slug(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        return HTMLResponse(
            content="<html><body style='font-family:sans-serif;text-align:center;padding:80px'><h1>404</h1><p>Proposal tidak ditemukan.</p></body></html>",
            status_code=404,
        )
    log_audit(db, "visitor", "VIEW", "proposals", proposal.id, {"slug": slug, "via": "short_link"})
    frontend_url = os.environ["FRONTEND_URL"]  # tidak ada fallback, harus dari env
    return RedirectResponse(url=f"{frontend_url}/proposal/{proposal.id}", status_code=307)


@app.get("/r/{slug}")
def report_og_redirect(slug: str, request: Request, db: Session = Depends(get_db)):
    frontend_url = _get_setting("frontend_url", os.environ["FRONTEND_URL"])
    report_url = f"{frontend_url}/report/{slug}"

    proposal = db.query(Proposal).filter(Proposal.slug == slug, Proposal.status == "Report").first()
    if not proposal:
        return RedirectResponse(url=report_url, status_code=307)

    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    business_name = lead.business_name if lead else "Bisnis Anda"
    category = lead.product_interest if lead else ""

    title = f"Hasil Audit Digital: {business_name}"
    description = f"Kami menemukan masalah kritis pada {business_name} yang membuat calon pelanggan lari ke kompetitor. Lihat laporan lengkap dan solusi yang kami rekomendasikan."
    og_image = f"https://api.kantorteman.my.id/api/og-image/{slug}"

    ua = (request.headers.get("user-agent") or "").lower()
    is_bot = any(b in ua for b in ["whatsapp", "facebookexternalhit", "telegrambot", "twitterbot", "linkedinbot", "slackbot", "bot", "crawler", "spider"])

    if not is_bot:
        return RedirectResponse(url=report_url, status_code=307)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{og_image}">
<meta property="og:url" content="https://api.kantorteman.my.id/r/{slug}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Kantor Teman">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{og_image}">
<meta http-equiv="refresh" content="0;url={report_url}">
</head>
<body><p>Redirecting to <a href="{report_url}">{report_url}</a>...</p></body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@app.get("/api/og-image/{slug}")
def og_image_simple(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug, Proposal.status == "Report").first()
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first() if proposal else None
    business_name = lead.business_name if lead else "Bisnis Anda"
    category = lead.product_interest if lead else ""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#09090b"/>
<rect width="1200" height="4" fill="#f59e0b"/>
<rect y="626" width="1200" height="4" fill="#10b981"/>
<text x="600" y="200" text-anchor="middle" font-family="Arial,sans-serif" font-size="24" fill="#a1a1aa" letter-spacing="2">LAPORAN HASIL AUDIT DIGITAL</text>
<text x="600" y="320" text-anchor="middle" font-family="Arial,sans-serif" font-size="52" font-weight="bold" fill="#fafafa">{business_name[:40]}</text>
<text x="600" y="380" text-anchor="middle" font-family="Arial,sans-serif" font-size="22" fill="#71717a">{category}</text>
<text x="600" y="520" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" fill="#52525b">Diterbitkan oleh Teman UMKM Kita Agensi</text>
</svg>"""
    return HTMLResponse(content=svg, status_code=200, media_type="image/svg+xml")


@app.get("/api/proposals/public/by-slug/{slug}")
def get_public_proposal_by_slug(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()

    now = datetime.now(timezone.utc)
    is_discount_expired = False
    active_price = proposal.discount_price or proposal.total_price
    if proposal.discount_expires_at:
        try:
            expires = datetime.fromisoformat(proposal.discount_expires_at.replace("Z", "+00:00"))
            if now > expires:
                is_discount_expired = True
                active_price = proposal.base_price or proposal.total_price
        except Exception:
            pass

    competitor_count = 0
    city = ""
    if lead and lead.address:
        city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else lead.address
    if lead and lead.product_interest and city:
        competitor_count = db.query(Lead).filter(
            Lead.product_interest == lead.product_interest,
            Lead.address.contains(city),
            Lead.id != lead.id,
            Lead.is_archived == False,
        ).count()

    services = json.loads(proposal.services_detail) if proposal.services_detail else []

    return {
        "id": proposal.id,
        "slug": proposal.slug,
        "business_name": lead.business_name if lead else None,
        "phone_number": lead.phone_number if lead else None,
        "address": lead.address if lead else None,
        "category": lead.product_interest if lead else None,
        "services_detail": services,
        "total_price": proposal.total_price,
        "base_price": proposal.base_price,
        "discount_price": proposal.discount_price,
        "discount_expires_at": proposal.discount_expires_at,
        "is_discount_expired": is_discount_expired,
        "active_price": active_price,
        "additional_options": proposal.additional_options,
        "status": proposal.status,
        "created_at": proposal.created_at,
        "competitor_count": competitor_count,
        "timeline_data": sorted(json.loads(proposal.timeline_data), key=lambda x: x["sequence"]) if proposal.timeline_data else [],
    }


@app.get("/api/proposals/public/report/{slug}")
def get_public_report_by_slug(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")

    # Set first_viewed_at on first open (lock di database)
    if not proposal.first_viewed_at:
        proposal.first_viewed_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        db.refresh(proposal)

    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()

    now = datetime.now(timezone.utc)
    is_discount_expired = False
    active_price = proposal.discount_price or proposal.total_price

    # Hitung deadline dari first_viewed_at + 24 jam
    discount_deadline = None
    if proposal.first_viewed_at:
        try:
            first_view = datetime.fromisoformat(proposal.first_viewed_at.replace("Z", "+00:00"))
            discount_deadline = (first_view + timedelta(hours=24)).isoformat()
            if now > first_view + timedelta(hours=24):
                is_discount_expired = True
                active_price = proposal.base_price or proposal.total_price
        except Exception:
            pass

    competitor_count = 0
    city = ""
    if lead and lead.address:
        city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else lead.address
    if lead and lead.product_interest and city:
        competitor_count = db.query(Lead).filter(
            Lead.product_interest == lead.product_interest,
            Lead.address.contains(city),
            Lead.id != lead.id,
            Lead.is_archived == False,
        ).count()

    # Data performa digital dari AI Scraper
    digital_analysis = None
    if lead:
        analysis_row = db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead.id).order_by(LeadAnalysis.id.desc()).first()
        if analysis_row:
            digital_analysis = {
                "analysis": analysis_row.analysis,
                "pain_points": json.loads(analysis_row.pain_points) if analysis_row.pain_points else [],
                "suggested_product": analysis_row.suggested_product,
                "analyzed_at": analysis_row.analyzed_at,
            }

    services = json.loads(proposal.services_detail) if proposal.services_detail else []

    return {
        "id": proposal.id,
        "slug": proposal.slug,
        "nama_usaha": lead.business_name if lead else None,
        "phone_number": lead.phone_number if lead else None,
        "address": lead.address if lead else None,
        "category": lead.product_interest if lead else None,
        "services_detail": services,
        "total_price": proposal.total_price,
        "base_price": proposal.base_price,
        "discount_price": proposal.discount_price,
        "discount_expires_at": discount_deadline,
        "is_discount_expired": is_discount_expired,
        "active_price": active_price,
        "first_viewed_at": proposal.first_viewed_at,
        "additional_options": proposal.additional_options,
        "status": proposal.status,
        "created_at": proposal.created_at,
        "competitor_count": competitor_count,
        "digital_analysis": digital_analysis,
        "faqs": json.loads(proposal.faqs) if proposal.faqs else [],
        "monthly_search_volume": get_monthly_search_volume(
            lead.product_interest or "",
            city if lead and lead.address else ""
        ) if lead else 500,
        "selected_addons": json.loads(proposal.selected_addons) if proposal.selected_addons and proposal.selected_addons != "[]" else [{"id": p.id, "name": p.name, "price": p.base_price} for p in db.query(Product).filter(Product.is_active == True).all()],
        "timeline_data": sorted(json.loads(proposal.timeline_data), key=lambda x: x["sequence"]) if proposal.timeline_data else [],
    }


@app.post("/api/proposals/public/report/{slug}/engage")
def engage_report(slug: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    non_upgrade_statuses = {"HOT_PROSPECT", "CLOSED"}
    if lead.status not in non_upgrade_statuses:
        lead.status = "HOT_PROSPECT"
        db.commit()
    return {"success": True, "status": lead.status}


def is_valid_customer_request(request: Request) -> bool:
    ua = (request.headers.get("user-agent") or "").lower()
    bot_signatures = ["whatsapp", "facebookexternalhit", "googlebot", "telegrambot", "twitterbot"]
    for sig in bot_signatures:
        if sig in ua:
            return False
    auth_header = request.headers.get("authorization") or ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return False
        except Exception:
            pass
    return True


SCORE_MAP = {
    "LINK_CLICKED": 30,
    "ROI_SLIDER_VIEWED": 25,
    "SHARE_PARTNER_CLICKED": 20,
    "IS_MOBILE": 10,
}


class TrackActivityBody(BaseModel):
    activity_type: str


@app.post("/api/proposals/public/report/{slug}/track-activity")
def track_activity(slug: str, body: TrackActivityBody, request: Request, db: Session = Depends(get_db)):
    if not is_valid_customer_request(request):
        return {"success": True, "filtered": True}
    proposal = db.query(Proposal).filter(Proposal.slug == slug).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")

    # Log activity ke LeadActivityLog (selalu insert untuk LINK_CLICKED)
    if body.activity_type == "LINK_CLICKED":
        db.add(LeadActivityLog(
            lead_id=lead.id,
            activity_type="LINK_CLICKED",
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        db.commit()

    points = SCORE_MAP.get(body.activity_type, 0)
    if points == 0:
        return {"success": True, "lead_score": lead.lead_score}
    # LINK_CLICKED score hanya ditambahkan sekali (jika score sudah >= 30, skip)
    if body.activity_type == "LINK_CLICKED" and (lead.lead_score or 0) >= 30:
        return {"success": True, "lead_score": lead.lead_score}
    new_score = min(100, (lead.lead_score or 0) + points)
    lead.lead_score = new_score
    db.commit()
    return {"success": True, "lead_score": new_score}


@app.get("/api/proposals/client/{lead_id}", response_model=list[ProposalOut])
def get_proposals_by_client(lead_id: int, source: str = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = None
    if source == "contact":
        contact = db.query(Contact).filter(Contact.id == lead_id).first()
        if contact:
            lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
    else:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            contact = db.query(Contact).filter(Contact.id == lead_id).first()
            if contact:
                lead = db.query(Lead).filter(Lead.phone_number == contact.phone_number).first()
    if not lead:
        return []
    proposals = db.query(Proposal).filter(Proposal.lead_id == lead.id).all()
    return [_proposal_to_out(p, lead) for p in proposals]


@app.get("/api/proposals", response_model=list[ProposalOut])
def get_proposals(include_archived: bool = Query(False), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Proposal)
    if not include_archived:
        query = query.filter(Proposal.is_archived == False)
    proposals = query.all()
    results = []
    for p in proposals:
        lead = db.query(Lead).filter(Lead.id == p.lead_id).first()
        results.append(_proposal_to_out(p, lead))
    return results


@app.delete("/api/proposals/{proposal_id}", status_code=204)
def delete_proposal(proposal_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    proposal.is_archived = True
    proposal.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    log_audit(db, current_user.name, "DELETE", "proposals", proposal_id, {"total_price": proposal.total_price})


@app.post("/api/proposals/restore/{proposal_id}", response_model=ProposalOut)
def restore_proposal(proposal_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    proposal.is_archived = False
    proposal.deleted_at = None
    db.commit()
    db.refresh(proposal)
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    log_audit(db, current_user.name, "RESTORE", "proposals", proposal_id, {})
    return _proposal_to_out(proposal, lead)


# ---------------------------------------------------------------------------
# Service Items (Daftar Jasa Dasar)
# ---------------------------------------------------------------------------

@app.get("/api/settings/services", response_model=list[ServiceItemOut])
def get_service_items(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    items = db.query(ServiceItem).all()
    results = []
    for item in items:
        results.append(ServiceItemOut(
            id=item.id,
            name=item.name,
            default_price=item.default_price,
            default_features=json.loads(item.default_features),
        ))
    return results


@app.post("/api/settings/services", response_model=ServiceItemOut, status_code=201)
def create_service_item(body: ServiceItemIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    item = ServiceItem(
        id=str(uuid.uuid4()),
        name=body.name,
        default_price=body.default_price,
        default_features=json.dumps(body.default_features),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ServiceItemOut(
        id=item.id,
        name=item.name,
        default_price=item.default_price,
        default_features=json.loads(item.default_features),
    )


@app.put("/api/settings/services/{item_id}", response_model=ServiceItemOut)
def update_service_item(item_id: str, body: ServiceItemIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Service item tidak ditemukan")
    item.name = body.name
    item.default_price = body.default_price
    item.default_features = json.dumps(body.default_features)
    db.commit()
    db.refresh(item)
    return ServiceItemOut(
        id=item.id,
        name=item.name,
        default_price=item.default_price,
        default_features=json.loads(item.default_features),
    )


@app.delete("/api/settings/services/{item_id}", status_code=204)
def delete_service_item(item_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(ServiceItem).filter(ServiceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Service item tidak ditemukan")
    db.delete(item)
    db.commit()


# ---------------------------------------------------------------------------
# Proposal Tracking (Public)
# ---------------------------------------------------------------------------

ADMIN_WA = os.getenv("ADMIN_WA", "6281234567890")


@app.post("/api/proposals/track/open")
async def track_open(body: TrackOpenIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):

    proposal = db.query(Proposal).filter(Proposal.id == body.proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal tidak ditemukan")
    lead = db.query(Lead).filter(Lead.id == proposal.lead_id).first()
    analytics = ProposalAnalytics(
        id=str(uuid.uuid4()),
        proposal_id=body.proposal_id,
        opened_at=datetime.now(timezone.utc).isoformat(),
        total_time_seconds=0,
        sections_viewed="[]",
    )
    db.add(analytics)
    db.commit()
    db.refresh(analytics)

    # Send WA notification to admin
    fonnte_token = get_fonnte_token(db)
    business_name = lead.business_name if lead else "Unknown"
    services = [s["name"] for s in json.loads(proposal.services_detail)]
    service_names = ", ".join(services) if services else "—"
    message = f"🚨 Mind Reader Alert: Klien {business_name} sedang membuka proposal [{service_names}] SEKARANG!"
    admin_wa = _get_setting("admin_wa", ADMIN_WA)
    background_tasks.add_task(send_fonnte_message, admin_wa, message, fonnte_token)

    # Re-engagement alert: if first viewed > 7 days ago
    if proposal.first_viewed_at and lead:
        try:
            first_view = datetime.fromisoformat(proposal.first_viewed_at.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - first_view).days >= 7:
                existing_alert = db.query(ReengagementAlert).filter(
                    ReengagementAlert.lead_id == lead.id,
                    ReengagementAlert.is_read == False,
                ).first()
                if not existing_alert:
                    db.add(ReengagementAlert(
                        id=str(uuid.uuid4()),
                        lead_id=lead.id,
                        proposal_id=proposal.id,
                        triggered_at=datetime.now(timezone.utc).isoformat(),
                    ))
                    db.commit()
        except Exception:
            pass

    return {"analytics_id": analytics.id}


@app.post("/api/proposals/track/ping")
def track_ping(body: TrackPingIn, db: Session = Depends(get_db)):

    analytics = db.query(ProposalAnalytics).filter(ProposalAnalytics.id == body.analytics_id).first()
    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics record tidak ditemukan")
    analytics.last_ping = datetime.now(timezone.utc).isoformat()
    analytics.total_time_seconds = (analytics.total_time_seconds or 0) + body.seconds
    existing_sections = json.loads(analytics.sections_viewed or "[]")
    for s in body.sections_viewed:
        if s not in existing_sections:
            existing_sections.append(s)
    analytics.sections_viewed = json.dumps(existing_sections)
    db.commit()
    return {"ok": True, "total_time_seconds": analytics.total_time_seconds}


@app.get("/api/proposals/{proposal_id}/analytics")
def get_proposal_analytics(proposal_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    records = db.query(ProposalAnalytics).filter(ProposalAnalytics.proposal_id == proposal_id).all()
    return [{
        "id": r.id,
        "proposal_id": r.proposal_id,
        "opened_at": r.opened_at,
        "last_ping": r.last_ping,
        "total_time_seconds": r.total_time_seconds,
        "sections_viewed": json.loads(r.sections_viewed or "[]"),
    } for r in records]


@app.get("/api/proposals/analytics/all")
def get_all_proposal_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = []
    proposals = db.query(Proposal).all()
    for p in proposals:
        records = db.query(ProposalAnalytics).filter(ProposalAnalytics.proposal_id == p.id).all()
        total_opens = len(records)
        total_time = sum(r.total_time_seconds or 0 for r in records)
        last_opened = max((r.opened_at for r in records), default=None) if records else None
        results.append({
            "proposal_id": p.id,
            "total_opens": total_opens,
            "total_time_seconds": total_time,
            "last_opened": last_opened,
        })
    return results


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@app.get("/api/analytics")
def get_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    total_clients = db.query(func.count(Contact.id)).scalar() or 0
    conversion_rate = round((total_clients / total_leads * 100), 1) if total_leads > 0 else 0.0

    rows = db.execute(
        select(func.lower(Lead.product_interest).label("product"), func.count(Lead.id).label("count"))
        .where(Lead.product_interest.isnot(None))
        .group_by(func.lower(Lead.product_interest))
        .order_by(func.count(Lead.id).desc())
    ).all()
    leads_by_product = [{"product": r[0].title() if r[0] else r[0], "count": r[1]} for r in rows]

    status_rows = db.execute(
        select(Lead.status, func.count(Lead.id).label("count")).group_by(Lead.status)
    ).all()
    leads_by_status = [{"status": r[0], "count": r[1]} for r in status_rows]

    return {
        "total_leads": total_leads,
        "total_clients": total_clients,
        "conversion_rate": conversion_rate,
        "leads_by_product": leads_by_product,
        "leads_by_status": leads_by_status,
    }


@app.get("/api/leads/hot")
def get_hot_leads(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    threshold_24h = (now - timedelta(hours=24)).isoformat()

    records = db.query(ProposalAnalytics, Proposal, Lead).join(
        Proposal, ProposalAnalytics.proposal_id == Proposal.id
    ).join(
        Lead, Proposal.lead_id == Lead.id
    ).filter(
        ProposalAnalytics.opened_at >= threshold_24h
    ).order_by(ProposalAnalytics.opened_at.desc()).all()

    seen_leads = {}
    for analytics, proposal, lead in records:
        if lead.id in seen_leads:
            seen_leads[lead.id]["total_opens"] += 1
            continue

        last_ping = analytics.last_ping
        opened_at = analytics.opened_at

        if last_ping:
            try:
                ping_time = datetime.fromisoformat(last_ping.replace("Z", "+00:00"))
                minutes_ago = (now - ping_time).total_seconds() / 60
            except Exception:
                minutes_ago = 999
        else:
            minutes_ago = 999

        if minutes_ago <= 5:
            status = "online"
        elif minutes_ago <= 60:
            status = "recent"
        else:
            status = "today"

        seen_leads[lead.id] = {
            "lead_id": lead.id,
            "business_name": lead.business_name,
            "phone_number": lead.phone_number,
            "category": lead.product_interest,
            "status": status,
            "last_active": last_ping or opened_at,
            "total_opens": 1,
            "proposal_slug": proposal.slug,
        }

    results = sorted(seen_leads.values(), key=lambda x: {"online": 0, "recent": 1, "today": 2}[x["status"]])
    return results


@app.get("/api/alerts/reengagement")
def get_reengagement_alerts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alerts = db.query(ReengagementAlert, Lead, Proposal).join(
        Lead, ReengagementAlert.lead_id == Lead.id
    ).join(
        Proposal, ReengagementAlert.proposal_id == Proposal.id
    ).filter(ReengagementAlert.is_read == False).order_by(ReengagementAlert.triggered_at.desc()).limit(20).all()

    results = []
    for alert, lead, proposal in alerts:
        days_since = 0
        if proposal.first_viewed_at:
            try:
                first_view = datetime.fromisoformat(proposal.first_viewed_at.replace("Z", "+00:00"))
                days_since = (datetime.now(timezone.utc) - first_view).days
            except Exception:
                pass
        results.append({
            "id": alert.id,
            "lead_id": lead.id,
            "business_name": lead.business_name,
            "phone_number": lead.phone_number,
            "category": lead.product_interest,
            "triggered_at": alert.triggered_at,
            "days_since_first_view": days_since,
            "proposal_slug": proposal.slug,
        })
    return results


@app.post("/api/alerts/reengagement/{alert_id}/read")
def mark_alert_read(alert_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(ReengagementAlert).filter(ReengagementAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert tidak ditemukan")
    alert.is_read = True
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Follow-up Sequence
# ---------------------------------------------------------------------------

@app.post("/api/followup/start")
def start_followup(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead_id = body.get("lead_id")
    template_ids = body.get("template_ids", [])
    delays = body.get("delays", [1, 3, 7])

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")

    existing = db.query(FollowUpSequence).filter(
        FollowUpSequence.lead_id == lead_id,
        FollowUpSequence.status == "ACTIVE",
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lead sudah punya sequence aktif")

    now = datetime.now(timezone.utc)
    next_send = (now + timedelta(days=delays[0])).isoformat() if delays else None

    seq = FollowUpSequence(
        id=str(uuid.uuid4()),
        lead_id=lead_id,
        template_ids=json.dumps(template_ids),
        delays=json.dumps(delays),
        current_step=0,
        status="ACTIVE",
        started_at=now.isoformat(),
        next_send_at=next_send,
    )
    db.add(seq)
    db.commit()
    db.refresh(seq)
    return {"id": seq.id, "status": seq.status, "next_send_at": seq.next_send_at}


@app.post("/api/followup/stop/{seq_id}")
def stop_followup(seq_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    seq = db.query(FollowUpSequence).filter(FollowUpSequence.id == seq_id).first()
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence tidak ditemukan")
    seq.status = "STOPPED"
    seq.stopped_reason = "manual"
    db.commit()
    return {"ok": True}


@app.get("/api/followup/active")
def get_active_followups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sequences = db.query(FollowUpSequence, Lead).join(
        Lead, FollowUpSequence.lead_id == Lead.id
    ).filter(FollowUpSequence.status == "ACTIVE").order_by(FollowUpSequence.next_send_at).all()

    results = []
    for seq, lead in sequences:
        delays = json.loads(seq.delays) if seq.delays else []
        results.append({
            "id": seq.id,
            "lead_id": lead.id,
            "business_name": lead.business_name,
            "phone_number": lead.phone_number,
            "current_step": seq.current_step,
            "total_steps": len(delays),
            "next_send_at": seq.next_send_at,
            "started_at": seq.started_at,
        })
    return results


@app.post("/api/followup/process")
async def process_followups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    sequences = db.query(FollowUpSequence).filter(
        FollowUpSequence.status == "ACTIVE",
        FollowUpSequence.next_send_at <= now.isoformat(),
    ).all()

    token = get_fonnte_token(db)
    sent_count = 0

    for seq in sequences:
        lead = db.query(Lead).filter(Lead.id == seq.lead_id).first()
        if not lead:
            seq.status = "STOPPED"
            seq.stopped_reason = "lead_not_found"
            db.commit()
            continue

        template_ids = json.loads(seq.template_ids) if seq.template_ids else []
        delays = json.loads(seq.delays) if seq.delays else []

        if seq.current_step >= len(delays):
            seq.status = "COMPLETED"
            db.commit()
            continue

        message = None
        if template_ids and seq.current_step < len(template_ids):
            tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == template_ids[seq.current_step]).first()
            if tmpl:
                message = tmpl.content.replace("{{business_name}}", lead.business_name).replace("{{client_name}}", lead.business_name)

        if not message:
            followup_defaults = [
                f"Halo {lead.business_name}, saya ingin follow up terkait laporan audit digital yang sudah saya kirimkan sebelumnya. Apakah ada pertanyaan yang bisa saya bantu jawab?",
                f"Pak, saya notice laporan audit untuk {lead.business_name} sudah dibuka tapi belum ada respons. Apakah ada kendala atau pertanyaan? Saya siap bantu jelaskan lebih detail.",
                f"Halo Pak, ini follow up terakhir dari saya untuk {lead.business_name}. Jika memang belum berminat saat ini, tidak masalah. Tapi perlu diingat, slot optimasi wilayah Anda terbatas dan kompetitor terus bergerak. Kapanpun siap, saya di sini.",
            ]
            message = followup_defaults[min(seq.current_step, len(followup_defaults) - 1)]

        await send_fonnte_message(lead.phone_number, message, token)
        sent_count += 1

        seq.current_step += 1
        if seq.current_step >= len(delays):
            seq.status = "COMPLETED"
            seq.next_send_at = None
        else:
            next_delay = delays[seq.current_step] if seq.current_step < len(delays) else 7
            seq.next_send_at = (now + timedelta(days=next_delay)).isoformat()
        db.commit()

    return {"processed": sent_count}


# ---------------------------------------------------------------------------
# Win/Loss Pattern Analysis
# ---------------------------------------------------------------------------

@app.get("/api/analytics/patterns")
def get_conversion_patterns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.is_archived == False).all()

    by_category = {}
    by_city = {}
    by_rating = {"high": {"total": 0, "converted": 0}, "mid": {"total": 0, "converted": 0}, "low": {"total": 0, "converted": 0}}

    for lead in leads:
        is_converted = lead.status == "Closed/Client"
        category = lead.product_interest or "Lainnya"
        city = lead.address.split(",")[-1].strip() if lead.address and "," in lead.address else (lead.address or "Unknown")

        if category not in by_category:
            by_category[category] = {"total": 0, "converted": 0}
        by_category[category]["total"] += 1
        if is_converted:
            by_category[category]["converted"] += 1

        if city not in by_city:
            by_city[city] = {"total": 0, "converted": 0}
        by_city[city]["total"] += 1
        if is_converted:
            by_city[city]["converted"] += 1

        rating = lead.rating or 0
        if rating >= 4:
            by_rating["high"]["total"] += 1
            if is_converted:
                by_rating["high"]["converted"] += 1
        elif rating >= 3:
            by_rating["mid"]["total"] += 1
            if is_converted:
                by_rating["mid"]["converted"] += 1
        else:
            by_rating["low"]["total"] += 1
            if is_converted:
                by_rating["low"]["converted"] += 1

    def calc_rate(d):
        return round((d["converted"] / d["total"] * 100), 1) if d["total"] > 0 else 0

    category_patterns = sorted([
        {"segment": k, "total": v["total"], "converted": v["converted"], "rate": calc_rate(v)}
        for k, v in by_category.items() if v["total"] >= 3
    ], key=lambda x: x["rate"], reverse=True)

    city_patterns = sorted([
        {"segment": k, "total": v["total"], "converted": v["converted"], "rate": calc_rate(v)}
        for k, v in by_city.items() if v["total"] >= 3
    ], key=lambda x: x["rate"], reverse=True)

    rating_patterns = [
        {"segment": "Rating 4-5", "total": by_rating["high"]["total"], "converted": by_rating["high"]["converted"], "rate": calc_rate(by_rating["high"])},
        {"segment": "Rating 3", "total": by_rating["mid"]["total"], "converted": by_rating["mid"]["converted"], "rate": calc_rate(by_rating["mid"])},
        {"segment": "Rating 0-2", "total": by_rating["low"]["total"], "converted": by_rating["low"]["converted"], "rate": calc_rate(by_rating["low"])},
    ]

    top_segment = category_patterns[0] if category_patterns else None
    recommendation = f"Fokus scrape lebih banyak di segment '{top_segment['segment']}' — conversion rate {top_segment['rate']}% (tertinggi)." if top_segment and top_segment["rate"] > 0 else "Belum cukup data untuk rekomendasi. Terus scrape dan blast untuk mengumpulkan pattern."

    return {
        "by_category": category_patterns[:10],
        "by_city": city_patterns[:10],
        "by_rating": rating_patterns,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Finance - Wallets
# ---------------------------------------------------------------------------

@app.get("/api/finance/wallets", response_model=list[WalletOut])
def get_wallets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Wallet).all()


@app.post("/api/finance/wallets", response_model=WalletOut, status_code=201)
def create_wallet(body: WalletIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = Wallet(**body.model_dump())
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


@app.put("/api/finance/wallets/{wallet_id}", response_model=WalletOut)
def update_wallet(wallet_id: int, body: WalletIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    wallet.name = body.name
    wallet.balance = body.balance
    wallet.icon = body.icon
    wallet.color = body.color
    db.commit()
    db.refresh(wallet)
    return wallet


@app.delete("/api/finance/wallets/{wallet_id}", status_code=204)
def delete_wallet(wallet_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    db.delete(wallet)
    db.commit()


# ---------------------------------------------------------------------------
# Finance - Transactions
# ---------------------------------------------------------------------------

@app.get("/api/finance/transactions", response_model=list[TransactionOut])
def get_transactions(
    wallet_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)
    if not include_archived:
        query = query.filter(Transaction.is_archived == False)
    if wallet_id:
        query = query.filter(Transaction.wallet_id == wallet_id)
    if type:
        query = query.filter(Transaction.type == type)
    transactions = query.order_by(Transaction.date.desc()).all()
    results = []
    for t in transactions:
        lead_name = None
        if t.lead_id:
            lead = db.query(Lead).filter(Lead.id == t.lead_id).first()
            lead_name = lead.business_name if lead else None
        results.append(TransactionOut(
            id=t.id, wallet_id=t.wallet_id, type=t.type, amount=t.amount,
            category=t.category, date=t.date, notes=t.notes,
            lead_id=t.lead_id, is_billed=t.is_billed, lead_name=lead_name,
        ))
    return results


@app.post("/api/finance/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(body: TransactionIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.id == body.wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    if body.type not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="Type harus 'income' atau 'expense'")
    txn = Transaction(**body.model_dump())
    db.add(txn)
    if body.type == "income":
        wallet.balance += body.amount
    else:
        wallet.balance -= body.amount
    db.commit()
    db.refresh(txn)
    log_audit(db, current_user.name, "CREATE", "transactions", txn.id, {"type": body.type, "amount": body.amount, "category": body.category})
    lead_name = None
    if txn.lead_id:
        lead = db.query(Lead).filter(Lead.id == txn.lead_id).first()
        lead_name = lead.business_name if lead else None
    return TransactionOut(
        id=txn.id, wallet_id=txn.wallet_id, type=txn.type, amount=txn.amount,
        category=txn.category, date=txn.date, notes=txn.notes,
        lead_id=txn.lead_id, is_billed=txn.is_billed, lead_name=lead_name,
    )


@app.put("/api/finance/transactions/{txn_id}", response_model=TransactionOut)
def update_transaction(txn_id: int, body: TransactionIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    wallet = db.query(Wallet).filter(Wallet.id == txn.wallet_id).first()
    if txn.type == "income":
        wallet.balance -= txn.amount
    else:
        wallet.balance += txn.amount
    txn.wallet_id = body.wallet_id
    txn.type = body.type
    txn.amount = body.amount
    txn.category = body.category
    txn.date = body.date
    txn.notes = body.notes
    txn.lead_id = body.lead_id
    txn.is_billed = body.is_billed
    new_wallet = db.query(Wallet).filter(Wallet.id == body.wallet_id).first()
    if body.type == "income":
        new_wallet.balance += body.amount
    else:
        new_wallet.balance -= body.amount
    db.commit()
    db.refresh(txn)
    lead_name = None
    if txn.lead_id:
        lead = db.query(Lead).filter(Lead.id == txn.lead_id).first()
        lead_name = lead.business_name if lead else None
    return TransactionOut(
        id=txn.id, wallet_id=txn.wallet_id, type=txn.type, amount=txn.amount,
        category=txn.category, date=txn.date, notes=txn.notes,
        lead_id=txn.lead_id, is_billed=txn.is_billed, lead_name=lead_name,
    )


@app.delete("/api/finance/transactions/{txn_id}", status_code=204)
def delete_transaction(txn_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    wallet = db.query(Wallet).filter(Wallet.id == txn.wallet_id).first()
    if txn.type == "income":
        wallet.balance -= txn.amount
    else:
        wallet.balance += txn.amount
    txn.is_archived = True
    txn.deleted_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    log_audit(db, current_user.name, "DELETE", "transactions", txn_id, {"amount": txn.amount, "category": txn.category})


@app.post("/api/finance/transactions/restore/{txn_id}", response_model=TransactionOut)
def restore_transaction(txn_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    wallet = db.query(Wallet).filter(Wallet.id == txn.wallet_id).first()
    if txn.type == "income":
        wallet.balance += txn.amount
    else:
        wallet.balance -= txn.amount
    txn.is_archived = False
    txn.deleted_at = None
    db.commit()
    db.refresh(txn)
    log_audit(db, current_user.name, "RESTORE", "transactions", txn_id, {"amount": txn.amount})
    lead_name = None
    if txn.lead_id:
        lead = db.query(Lead).filter(Lead.id == txn.lead_id).first()
        lead_name = lead.business_name if lead else None
    return TransactionOut(
        id=txn.id, wallet_id=txn.wallet_id, type=txn.type, amount=txn.amount,
        category=txn.category, date=txn.date, notes=txn.notes,
        lead_id=txn.lead_id, is_billed=txn.is_billed, lead_name=lead_name,
    )


# ---------------------------------------------------------------------------
# Finance - Subscriptions
# ---------------------------------------------------------------------------

@app.get("/api/finance/subscriptions", response_model=list[SubscriptionOut])
def get_subscriptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subs = db.query(Subscription).all()
    results = []
    for s in subs:
        wallet = db.query(Wallet).filter(Wallet.id == s.wallet_id).first()
        results.append(SubscriptionOut(
            id=s.id, wallet_id=s.wallet_id, name=s.name, amount=s.amount,
            billing_cycle=s.billing_cycle, next_billing_date=s.next_billing_date,
            is_active=s.is_active, wallet_name=wallet.name if wallet else None,
        ))
    return results


@app.post("/api/finance/subscriptions", response_model=SubscriptionOut, status_code=201)
def create_subscription(body: SubscriptionIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.id == body.wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    if body.billing_cycle not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="billing_cycle harus 'monthly' atau 'yearly'")
    sub = Subscription(**body.model_dump())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return SubscriptionOut(
        id=sub.id, wallet_id=sub.wallet_id, name=sub.name, amount=sub.amount,
        billing_cycle=sub.billing_cycle, next_billing_date=sub.next_billing_date,
        is_active=sub.is_active, wallet_name=wallet.name,
    )


@app.put("/api/finance/subscriptions/{sub_id}", response_model=SubscriptionOut)
def update_subscription(sub_id: int, body: SubscriptionIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription tidak ditemukan")
    wallet = db.query(Wallet).filter(Wallet.id == body.wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet tidak ditemukan")
    sub.wallet_id = body.wallet_id
    sub.name = body.name
    sub.amount = body.amount
    sub.billing_cycle = body.billing_cycle
    sub.next_billing_date = body.next_billing_date
    sub.is_active = body.is_active
    db.commit()
    db.refresh(sub)
    return SubscriptionOut(
        id=sub.id, wallet_id=sub.wallet_id, name=sub.name, amount=sub.amount,
        billing_cycle=sub.billing_cycle, next_billing_date=sub.next_billing_date,
        is_active=sub.is_active, wallet_name=wallet.name,
    )


@app.delete("/api/finance/subscriptions/{sub_id}", status_code=204)
def delete_subscription(sub_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription tidak ditemukan")
    db.delete(sub)
    db.commit()


# ---------------------------------------------------------------------------
# Finance - Reports
# ---------------------------------------------------------------------------

@app.get("/api/finance/reports", response_model=FinanceReportOut)
def get_finance_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_balance = db.query(func.coalesce(func.sum(Wallet.balance), 0)).scalar() or 0

    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    monthly_expenses = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.type == "expense",
        Transaction.date.like(f"{current_month}%"),
    ).scalar() or 0

    total_subscription_monthly = 0
    active_subs = db.query(Subscription).filter(Subscription.is_active == True).all()
    for sub in active_subs:
        if sub.billing_cycle == "monthly":
            total_subscription_monthly += sub.amount
        else:
            total_subscription_monthly += sub.amount / 12

    break_even_point = monthly_expenses + total_subscription_monthly

    financial_runway = round(total_balance / break_even_point, 1) if break_even_point > 0 else 99.0

    category_rows = db.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("total"))
        .where(Transaction.type == "expense", Transaction.date.like(f"{current_month}%"))
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()
    expense_by_category = [{"category": r[0] or "Lainnya", "amount": r[1]} for r in category_rows]

    return FinanceReportOut(
        total_balance=total_balance,
        break_even_point=break_even_point,
        financial_runway_months=financial_runway,
        expense_by_category=expense_by_category,
    )


# ---------------------------------------------------------------------------
# Finance - Auto-Deduct Subscriptions (Scheduler Endpoint)
# ---------------------------------------------------------------------------

@app.post("/api/finance/subscriptions/auto-deduct")
def auto_deduct_subscriptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.now().strftime("%Y-%m-%d")
    subs = db.query(Subscription).filter(
        Subscription.is_active == True,
        Subscription.next_billing_date <= today,
    ).all()
    deducted = []
    for sub in subs:
        wallet = db.query(Wallet).filter(Wallet.id == sub.wallet_id).first()
        if not wallet:
            continue
        txn = Transaction(
            wallet_id=sub.wallet_id,
            type="expense",
            amount=sub.amount,
            category="Subscription",
            date=today,
            notes=f"Auto-deduct: {sub.name}",
        )
        db.add(txn)
        wallet.balance -= sub.amount
        next_date = datetime.strptime(sub.next_billing_date, "%Y-%m-%d")
        if sub.billing_cycle == "monthly":
            next_date = next_date.replace(month=next_date.month % 12 + 1, year=next_date.year + (1 if next_date.month == 12 else 0))
        else:
            next_date = next_date.replace(year=next_date.year + 1)
        sub.next_billing_date = next_date.strftime("%Y-%m-%d")
        deducted.append({"subscription": sub.name, "amount": sub.amount, "next_billing_date": sub.next_billing_date})
    db.commit()
    return {"deducted_count": len(deducted), "details": deducted}


# ---------------------------------------------------------------------------
# Finance - Client Unbilled Expenses (for CRM integration)
# ---------------------------------------------------------------------------

@app.get("/api/finance/client/{lead_id}/unbilled")
def get_client_unbilled(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transactions = db.query(Transaction).filter(
        Transaction.lead_id == lead_id,
        Transaction.type == "expense",
        Transaction.is_billed == False,
    ).all()
    total = sum(t.amount for t in transactions)
    return {"lead_id": lead_id, "unbilled_total": total, "count": len(transactions)}


@app.get("/api/clients/detail/{client_id}")
def get_client_detail(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == client_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Klien tidak ditemukan")

    # Projects
    client_projects = db.query(Project).filter(Project.lead_id == client_id).all()
    projects_out = [{
        "id": p.id, "name": p.name, "type": p.type, "status": p.status,
        "nominal": p.nominal, "start_date": p.start_date, "end_date": p.end_date,
    } for p in client_projects]

    # LTV: For FIXED = nominal, For RETAINER = nominal × months elapsed since start
    ltv = 0
    for p in client_projects:
        if p.status not in ("ACTIVE", "COMPLETED"):
            continue
        if p.type == "RETAINER" and p.start_date:
            start = datetime.strptime(p.start_date, "%Y-%m-%d")
            now = datetime.now()
            months_elapsed = (now.year - start.year) * 12 + (now.month - start.month) + 1
            ltv += p.nominal * months_elapsed
        else:
            ltv += p.nominal

    # Active billing (ACTIVE projects total)
    active_billing = sum(p.nominal for p in client_projects if p.status == "ACTIVE")

    # Dana Talangan (unbilled linked expenses)
    unbilled_txns = db.query(Transaction).filter(
        Transaction.lead_id == client_id,
        Transaction.type == "expense",
        Transaction.is_billed == False,
    ).all()
    dana_talangan = sum(t.amount for t in unbilled_txns)

    # Notes
    notes = db.query(ClientNote).filter(ClientNote.lead_id == client_id).order_by(ClientNote.id.desc()).all()
    notes_out = [{
        "id": n.id, "category": n.category, "content": n.content,
        "actor": n.actor, "timestamp": n.timestamp,
    } for n in notes]

    return {
        "profile": {
            "id": contact.id,
            "business_name": contact.business_name,
            "owner_name": contact.owner_name,
            "phone_number": contact.phone_number,
            "purchased_product": contact.purchased_product,
            "notes": contact.notes,
        },
        "ltv": ltv,
        "active_billing": active_billing,
        "dana_talangan": dana_talangan,
        "projects": projects_out,
        "notes": notes_out,
    }


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@app.get("/api/audit-logs")
def get_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(AuditLog.id)).scalar() or 0
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "logs": [{
            "id": log.id,
            "timestamp": log.timestamp,
            "actor": log.actor,
            "action": log.action,
            "table_name": log.table_name,
            "record_id": log.record_id,
            "details": json.loads(log.details) if log.details else None,
        } for log in logs],
    }


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------

@app.get("/api/export/leads")
def export_leads_csv(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.is_archived == False).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Nama Bisnis", "Nomor Telepon", "Alamat", "Status", "Produk", "Batch", "Rating"])
    for l in leads:
        writer.writerow([l.id, l.business_name, l.phone_number, l.address or "", l.status, l.product_interest or "", l.batch_name or "", l.rating])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )


@app.get("/api/export/finance")
def export_finance_csv(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    transactions = db.query(Transaction).filter(Transaction.is_archived == False).order_by(Transaction.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Wallet ID", "Tipe", "Jumlah", "Kategori", "Tanggal", "Catatan", "Lead ID", "Sudah Ditagih"])
    for t in transactions:
        writer.writerow([t.id, t.wallet_id, t.type, t.amount, t.category or "", t.date, t.notes or "", t.lead_id or "", t.is_billed])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance_export.csv"},
    )


# ---------------------------------------------------------------------------
# Master Data - Categories
# ---------------------------------------------------------------------------

@app.get("/api/categories", response_model=list[CategoryOut])
def get_categories(
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Category)
    if active_only:
        query = query.filter(Category.is_active == True)
    return query.all()


@app.post("/api/categories", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Kategori dengan nama ini sudah ada")
    cat = Category(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        is_active=body.is_active,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    log_audit(db, current_user.name, "CREATE", "categories", cat.id, {"name": body.name})
    return cat


@app.put("/api/categories/{cat_id}", response_model=CategoryOut)
def update_category(cat_id: str, body: CategoryIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    dup = db.query(Category).filter(Category.name == body.name, Category.id != cat_id).first()
    if dup:
        raise HTTPException(status_code=400, detail="Kategori dengan nama ini sudah ada")
    cat.name = body.name
    cat.description = body.description
    cat.is_active = body.is_active
    db.commit()
    db.refresh(cat)
    log_audit(db, current_user.name, "UPDATE", "categories", cat_id, {"name": body.name})
    return cat


@app.delete("/api/categories/{cat_id}", status_code=204)
def delete_category(cat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    db.delete(cat)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "categories", cat_id, {"name": cat.name})


# ---------------------------------------------------------------------------
# Master Data - Products
# ---------------------------------------------------------------------------

def _product_to_out(product, db) -> ProductOut:
    cat_name = None
    if product.category_id:
        cat = db.query(Category).filter(Category.id == product.category_id).first()
        cat_name = cat.name if cat else None
    return ProductOut(
        id=product.id, name=product.name, description=product.description,
        base_price=product.base_price, features=json.loads(product.features or "[]"),
        category_id=product.category_id, category_name=cat_name, is_active=product.is_active,
        is_retainer=product.is_retainer or False,
    )


@app.get("/api/products", response_model=list[ProductOut])
def get_products(
    category_id: Optional[str] = Query(None),
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    products = query.all()
    return [_product_to_out(p, db) for p in products]


@app.post("/api/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = Product(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        base_price=body.base_price,
        features=json.dumps(body.features),
        category_id=body.category_id,
        is_active=body.is_active,
        is_retainer=body.is_retainer,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    log_audit(db, current_user.name, "CREATE", "products", product.id, {"name": body.name})
    return _product_to_out(product, db)


@app.put("/api/products/{product_id}", response_model=ProductOut)
def update_product(product_id: str, body: ProductIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    product.name = body.name
    product.description = body.description
    product.base_price = body.base_price
    product.features = json.dumps(body.features)
    product.category_id = body.category_id
    product.is_active = body.is_active
    product.is_retainer = body.is_retainer
    db.commit()
    db.refresh(product)
    log_audit(db, current_user.name, "UPDATE", "products", product_id, {"name": body.name})
    return _product_to_out(product, db)


@app.delete("/api/products/{product_id}", status_code=204)
def delete_product(product_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    db.delete(product)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "products", product_id, {"name": product.name})


# ---------------------------------------------------------------------------
# Master Data - Dynamic Templates
# ---------------------------------------------------------------------------

VALID_TEMPLATE_TYPES = {"WA_BLAST", "PROPOSAL_TEXT", "PROPOSAL_INTRO", "PROPOSAL_OUTRO", "FOLLOW_UP", "GENERAL"}


@app.get("/api/dynamic-templates", response_model=list[DynamicTemplateOut])
def get_dynamic_templates(
    type: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(DynamicTemplate)
    if active_only:
        query = query.filter(DynamicTemplate.is_active == True)
    if type:
        query = query.filter(DynamicTemplate.type == type)
    if category_id:
        query = query.filter(DynamicTemplate.category_id == category_id)
    templates = query.all()
    results = []
    for t in templates:
        cat_name = None
        if t.category_id:
            cat = db.query(Category).filter(Category.id == t.category_id).first()
            cat_name = cat.name if cat else None
        results.append(DynamicTemplateOut(
            id=t.id, name=t.name, type=t.type, content=t.content,
            is_active=t.is_active, category_id=t.category_id, category_name=cat_name,
        ))
    return results


@app.post("/api/dynamic-templates", response_model=DynamicTemplateOut, status_code=201)
def create_dynamic_template(body: DynamicTemplateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.type not in VALID_TEMPLATE_TYPES:
        raise HTTPException(status_code=400, detail=f"Type harus salah satu dari: {', '.join(VALID_TEMPLATE_TYPES)}")
    tmpl = DynamicTemplate(
        id=str(uuid.uuid4()),
        name=body.name,
        type=body.type,
        content=body.content,
        is_active=body.is_active,
        category_id=body.category_id,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    log_audit(db, current_user.name, "CREATE", "dynamic_templates", tmpl.id, {"name": body.name, "type": body.type})
    cat_name = None
    if tmpl.category_id:
        cat = db.query(Category).filter(Category.id == tmpl.category_id).first()
        cat_name = cat.name if cat else None
    return DynamicTemplateOut(
        id=tmpl.id, name=tmpl.name, type=tmpl.type, content=tmpl.content,
        is_active=tmpl.is_active, category_id=tmpl.category_id, category_name=cat_name,
    )


@app.put("/api/dynamic-templates/{tmpl_id}", response_model=DynamicTemplateOut)
def update_dynamic_template(tmpl_id: str, body: DynamicTemplateIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    if body.type not in VALID_TEMPLATE_TYPES:
        raise HTTPException(status_code=400, detail=f"Type harus salah satu dari: {', '.join(VALID_TEMPLATE_TYPES)}")
    tmpl.name = body.name
    tmpl.type = body.type
    tmpl.content = body.content
    tmpl.is_active = body.is_active
    tmpl.category_id = body.category_id
    db.commit()
    db.refresh(tmpl)
    log_audit(db, current_user.name, "UPDATE", "dynamic_templates", tmpl_id, {"name": body.name})
    cat_name = None
    if tmpl.category_id:
        cat = db.query(Category).filter(Category.id == tmpl.category_id).first()
        cat_name = cat.name if cat else None
    return DynamicTemplateOut(
        id=tmpl.id, name=tmpl.name, type=tmpl.type, content=tmpl.content,
        is_active=tmpl.is_active, category_id=tmpl.category_id, category_name=cat_name,
    )


@app.delete("/api/dynamic-templates/{tmpl_id}", status_code=204)
def delete_dynamic_template(tmpl_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == tmpl_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template tidak ditemukan")
    db.delete(tmpl)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "dynamic_templates", tmpl_id, {"name": tmpl.name})


# ---------------------------------------------------------------------------
# Timeline Templates API
# ---------------------------------------------------------------------------

@app.get("/api/timeline-templates")
def get_timeline_templates(db: Session = Depends(get_db)):
    templates = db.query(DynamicTemplate).filter(
        DynamicTemplate.type == "TIMELINE_TEMPLATE",
        DynamicTemplate.is_active == True,
    ).all()
    result = []
    for t in templates:
        items = json.loads(t.content) if t.content else []
        sorted_items = sorted(items, key=lambda x: x.get("sequence", 0))
        result.append({
            "id": t.id,
            "name": t.name,
            "category_id": t.category_id,
            "timeline_data": sorted_items,
        })
    return result


# ---------------------------------------------------------------------------
# AI Lead Analysis (Multi-Provider: Gemini, Claude, OpenAI)
# ---------------------------------------------------------------------------

def get_ai_config(db: Session) -> dict:
    provider = db.query(SystemSettings).filter_by(key="ai_provider").first()
    gemini = db.query(SystemSettings).filter_by(key="gemini_api_key").first()
    claude = db.query(SystemSettings).filter_by(key="claude_api_key").first()
    openai = db.query(SystemSettings).filter_by(key="openai_api_key").first()
    base_url = db.query(SystemSettings).filter_by(key="ai_base_url").first()
    model = db.query(SystemSettings).filter_by(key="ai_model").first()
    return {
        "provider": (provider.value if provider else "gemini"),
        "gemini_key": (gemini.value if gemini else ""),
        "claude_key": (claude.value if claude else ""),
        "openai_key": (openai.value if openai else ""),
        "base_url": (base_url.value if base_url else ""),
        "model": (model.value if model else ""),
    }


def build_analysis_prompt(lead, product_list: str) -> str:
    return f"""Kamu adalah konsultan digital marketing untuk UMKM Indonesia. Analisa bisnis berikut dan berikan insight yang persuasif dan mudah dipahami pemilik usaha.

DATA BISNIS:
- Nama: {lead.business_name}
- Alamat: {lead.address or 'Tidak diketahui'}
- Rating Google: {lead.rating}/5
- Kategori: {lead.product_interest or 'Umum'}

PRODUK/LAYANAN YANG KAMI TAWARKAN:
{product_list}

INSTRUKSI:
Berikan output dalam format JSON berikut (Bahasa Indonesia, gaya bicara santai tapi profesional):
{{
  "pain_points": ["masalah 1 yang spesifik dan relatable untuk pemilik usaha", "masalah 2", "masalah 3"],
  "suggested_product": "nama produk kami yang paling cocok",
  "approach_message": "satu paragraf pendek pesan WA yang bisa langsung dikirim ke pemilik bisnis ini, persuasif tapi tidak memaksa, sebutkan masalah mereka dan solusi kita"
}}

PENTING: Pain points harus spesifik ke bisnis ini, bukan generik. Pesan pendekatan harus terasa personal."""


def _call_ai_sync(prompt: str, config: dict, _httpx) -> str:
    provider = config["provider"]
    with _httpx.Client(timeout=120) as client:
        if provider == "gemini":
            if not config["gemini_key"]:
                raise Exception("Gemini API Key belum dikonfigurasi.")
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={config['gemini_key']}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            if resp.status_code != 200:
                raise Exception(f"Gemini API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        elif provider == "claude":
            if not config["claude_key"]:
                raise Exception("Claude API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "claude-haiku-4-5-20251001"
            url = f"{base_url.rstrip('/')}/chat/completions"
            print(f"[AI CALL SYNC] url={url} model={model}", flush=True)
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {config['claude_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            print(f"[AI RESPONSE SYNC] status={resp.status_code} length={len(resp.text)}", flush=True)
            if resp.status_code != 200:
                raise Exception(f"Claude API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]
        elif provider == "openai":
            if not config["openai_key"]:
                raise Exception("OpenAI API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "gpt-4o-mini"
            resp = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['openai_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                },
            )
            if resp.status_code != 200:
                raise Exception(f"OpenAI API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Provider '{provider}' tidak dikenali.")


async def call_ai_provider(prompt: str, config: dict) -> str:
    provider = config["provider"]
    async with httpx.AsyncClient(timeout=60) as client:
        if provider == "gemini":
            if not config["gemini_key"]:
                raise HTTPException(status_code=400, detail="Gemini API Key belum dikonfigurasi.")
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={config['gemini_key']}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Gemini API error: {resp.status_code}")
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

        elif provider == "claude":
            if not config["claude_key"]:
                raise HTTPException(status_code=400, detail="Claude API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "claude-haiku-4-5-20251001"
            url = f"{base_url.rstrip('/')}/chat/completions"
            print(f"[AI CALL] provider=claude url={url} model={model} key={config['claude_key'][:10]}...", flush=True)
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {config['claude_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            print(f"[AI RESPONSE] status={resp.status_code} length={len(resp.text)}", flush=True)
            if resp.status_code != 200:
                print(f"[AI CALL ERROR] status={resp.status_code} body={resp.text[:500]}", flush=True)
                raise HTTPException(status_code=502, detail=f"Claude API error: {resp.status_code} - {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]

        elif provider == "openai":
            if not config["openai_key"]:
                raise HTTPException(status_code=400, detail="OpenAI API Key belum dikonfigurasi.")
            base_url = config.get("base_url") or "https://api.openai.com/v1"
            model = config.get("model") or "gpt-4o-mini"
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['openai_key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"OpenAI API error: {resp.status_code}")
            return resp.json()["choices"][0]["message"]["content"]

        else:
            raise HTTPException(status_code=400, detail=f"Provider '{provider}' tidak dikenali.")


def parse_ai_response(text: str) -> dict:
    import re as _re
    json_match = _re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass
    return {"pain_points": [text], "suggested_product": "", "approach_message": ""}


@app.post("/api/leads/{lead_id}/generate-report")
def generate_report_endpoint(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    slug = generate_report_for_lead(lead, db)
    frontend_url = _get_setting("frontend_url", os.environ["FRONTEND_URL"])
    return {"slug": slug, "report_url": f"https://api.kantorteman.my.id/r/{slug}"}


@app.post("/api/leads/{lead_id}/analyze")
async def analyze_lead(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    config = get_ai_config(db)

    products = db.query(Product).filter(Product.is_active == True).all()
    product_list = "\n".join([f"- {p.name}: {p.description or ''}" for p in products]) if products else "- SEO\n- Web Development\n- Social Media Management"

    prompt = build_analysis_prompt(lead, product_list)

    try:
        text = await call_ai_provider(prompt, config)
        parsed = parse_ai_response(text)

        input_tokens = len(prompt) // 4
        output_tokens = len(text) // 4
        log_ai_cost(db, None, config["provider"], input_tokens, output_tokens)

        analysis = LeadAnalysis(
            lead_id=lead_id,
            analysis=text,
            pain_points=json.dumps(parsed.get("pain_points", [])),
            suggested_product=parsed.get("suggested_product", ""),
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return {
            "id": analysis.id,
            "lead_id": lead_id,
            "analysis": text,
            "pain_points": parsed.get("pain_points", []),
            "suggested_product": parsed.get("suggested_product", ""),
            "approach_message": parsed.get("approach_message", ""),
            "analyzed_at": analysis.analyzed_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menganalisa: {str(e)}")


@app.get("/api/leads/{lead_id}/analysis")
def get_lead_analysis(lead_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead_id).order_by(LeadAnalysis.id.desc()).all()
    results = []
    for a in analyses:
        results.append({
            "id": a.id,
            "lead_id": a.lead_id,
            "analysis": a.analysis,
            "pain_points": json.loads(a.pain_points) if a.pain_points else [],
            "suggested_product": a.suggested_product,
            "analyzed_at": a.analyzed_at,
        })
    return results


@app.post("/api/leads/analyze-batch")
async def analyze_batch(
    batch_name: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    config = get_ai_config(db)
    leads = db.query(Lead).filter(Lead.batch_name == batch_name, Lead.is_archived == False).all()
    already_analyzed = {a.lead_id for a in db.query(LeadAnalysis.lead_id).all()}
    to_analyze = [l for l in leads if l.id not in already_analyzed]
    if not to_analyze:
        return {"message": "Semua lead di batch ini sudah dianalisa.", "analyzed": 0, "total": 0, "status": "done"}

    # Store job status in memory
    job_id = batch_name
    _analysis_jobs[job_id] = {"status": "running", "total": len(to_analyze), "analyzed": 0, "batch_name": batch_name}

    # Run in background thread (WSGI kills event loop after response)
    def run_analysis_sync():
        import httpx as _httpx
        import time as _time
        from sqlalchemy import create_engine as _ce
        from sqlalchemy.orm import sessionmaker as _sm
        _ca = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        _engine = _ce(DATABASE_URL, connect_args=_ca, pool_recycle=60, pool_pre_ping=True, pool_size=1, max_overflow=0)
        _Session = _sm(bind=_engine)
        try:
            _db = _Session()
            _config = get_ai_config(_db)
            _products = _db.query(Product).filter(Product.is_active == True).all()
            _product_list = "\n".join([f"- {p.name}: {p.description or ''}" for p in _products]) if _products else "- SEO\n- Web Development"
            _db.close()
            analyzed = 0
            for lead in to_analyze[:20]:
                prompt = build_analysis_prompt(lead, _product_list)
                try:
                    text = _call_ai_sync(prompt, _config, _httpx)
                    parsed = parse_ai_response(text)
                    _db = _Session()
                    _db.add(LeadAnalysis(
                        lead_id=lead.id,
                        analysis=text,
                        pain_points=json.dumps(parsed.get("pain_points", [])),
                        suggested_product=parsed.get("suggested_product", ""),
                        analyzed_at=datetime.now(timezone.utc).isoformat(),
                    ))
                    _db.commit()
                    _db.close()
                    analyzed += 1
                    _analysis_jobs[job_id]["analyzed"] = analyzed
                    print(f"[AI ANALYZE PROGRESS] {analyzed}/{len(to_analyze)} lead_id={lead.id}", flush=True)
                    _time.sleep(1)
                except Exception as e:
                    import traceback
                    print(f"[AI ANALYZE ERROR] lead={lead.id} error={e}", flush=True)
                    traceback.print_exc()
                    _analysis_jobs[job_id]["error"] = str(e)
                    _analysis_jobs[job_id]["failed"] = _analysis_jobs[job_id].get("failed", 0) + 1
                    try:
                        _db.close()
                    except Exception:
                        pass
                    continue
            _analysis_jobs[job_id]["status"] = "done"
            _analysis_jobs[job_id]["analyzed"] = analyzed
            print(f"[AI ANALYZE DONE] analyzed={analyzed}/{len(to_analyze)} failed={_analysis_jobs[job_id].get('failed', 0)}", flush=True)
        except Exception as e:
            import traceback
            print(f"[AI ANALYZE FATAL] error={e}", flush=True)
            traceback.print_exc()
            _analysis_jobs[job_id]["status"] = "error"
            _analysis_jobs[job_id]["error"] = str(e)
        finally:
            _engine.dispose()

    import threading
    threading.Thread(target=run_analysis_sync, daemon=True).start()
    return {"message": f"Analisa dimulai untuk {len(to_analyze)} leads.", "analyzed": 0, "total": len(to_analyze), "status": "running", "job_id": job_id}


# In-memory job tracker
_analysis_jobs: dict = {}
_blast_jobs: dict = {}


@app.get("/api/leads/analyze-status")
def get_analyze_status(
    batch_name: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    job = _analysis_jobs.get(batch_name)
    if not job:
        return {"status": "idle", "analyzed": 0, "total": 0}
    return job


@app.get("/api/campaign/blast-status")
def get_blast_status(
    batch_name: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    job = _blast_jobs.get(batch_name)
    if not job:
        return {"status": "idle", "sent": 0, "total": 0}
    return job


@app.get("/api/background-jobs")
def get_all_background_jobs(current_user: User = Depends(get_current_user)):
    jobs = []
    for name, job in _analysis_jobs.items():
        jobs.append({**job, "type": "analysis", "batch_name": name})
    for name, job in _blast_jobs.items():
        jobs.append({**job, "type": "blast", "batch_name": name})
    return jobs


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.get("/api/projects", response_model=list[ProjectOut])
def get_projects(
    lead_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Project)
    if lead_id:
        query = query.filter(Project.lead_id == lead_id)
    if status:
        query = query.filter(Project.status == status)
    return query.all()


@app.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.type not in ("FIXED", "RETAINER"):
        raise HTTPException(status_code=400, detail="Type harus 'FIXED' atau 'RETAINER'")
    if body.status not in ("ACTIVE", "COMPLETED", "HOLD"):
        raise HTTPException(status_code=400, detail="Status harus 'ACTIVE', 'COMPLETED', atau 'HOLD'")
    project = Project(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        name=body.name,
        type=body.type,
        status=body.status,
        nominal=body.nominal,
        start_date=body.start_date,
        end_date=body.end_date,
        color=body.color or "yellow",
    )
    db.add(project)
    db.flush()  # Get project.id without committing

    # Auto-create board with default columns
    board = Board(id=str(uuid.uuid4()), project_id=project.id)
    db.add(board)
    db.flush()

    # Default columns: To Do, In Progress, Review, Done
    default_columns = [
        ("To Do", "yellow"),
        ("In Progress", "blue"),
        ("Review", "purple"),
        ("Done", "green"),
    ]
    for i, (name, color) in enumerate(default_columns):
        col = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=name, position=i, color=color)
        db.add(col)

    db.commit()
    db.refresh(project)
    log_audit(db, current_user.name, "CREATE", "projects", project.id, {"name": body.name, "lead_id": body.lead_id})
    return project


@app.put("/api/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, body: ProjectIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    project.lead_id = body.lead_id
    project.name = body.name
    project.type = body.type
    project.status = body.status
    project.nominal = body.nominal
    project.start_date = body.start_date
    project.end_date = body.end_date
    project.color = body.color or "yellow"
    db.commit()
    db.refresh(project)
    log_audit(db, current_user.name, "UPDATE", "projects", project_id, {"name": body.name})
    return project


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    # Cascade delete: board → columns → cards → children
    board = db.query(Board).filter(Board.project_id == project_id).first()
    if board:
        col_ids = [c.id for c in db.query(BoardColumn.id).filter(BoardColumn.board_id == board.id).all()]
        if col_ids:
            card_ids = [c.id for c in db.query(BoardCard.id).filter(BoardCard.column_id.in_(col_ids)).all()]
            if card_ids:
                db.query(BoardCardActivity).filter(BoardCardActivity.card_id.in_(card_ids)).delete(synchronize_session=False)
                db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id.in_(card_ids)).delete(synchronize_session=False)
                db.query(BoardCardComment).filter(BoardCardComment.card_id.in_(card_ids)).delete(synchronize_session=False)
            db.query(BoardCard).filter(BoardCard.column_id.in_(col_ids)).delete(synchronize_session=False)
        db.query(BoardColumn).filter(BoardColumn.board_id == board.id).delete(synchronize_session=False)
        db.delete(board)
    project_name = project.name
    db.delete(project)
    db.commit()
    log_audit(db, current_user.name, "DELETE", "projects", project_id, {"name": project_name})


@app.patch("/api/projects/{project_id}/archive")
def archive_project(
    project_id: str,
    is_archived: bool = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    project.is_archived = is_archived
    db.commit()
    return {"id": project_id, "is_archived": is_archived}


@app.patch("/api/projects/{project_id}/color")
def update_project_color(
    project_id: str,
    color: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    project.color = color
    db.commit()
    return {"id": project_id, "color": color}


# ---------------------------------------------------------------------------
# Board API (Trello-like)
# ---------------------------------------------------------------------------

def card_to_out(card: BoardCard) -> BoardCardOut:
    """Convert BoardCard to BoardCardOut with related data"""
    labels_list = []
    if card.labels:
        try:
            labels_list = json.loads(card.labels) if isinstance(card.labels, str) else card.labels
        except:
            labels_list = []

    lead_out = None
    if card.lead_id and card.lead:
        lead_out = LeadMin(id=card.lead.id, business_name=card.lead.business_name)

    return BoardCardOut(
        id=card.id,
        column_id=card.column_id,
        title=card.title,
        description=card.description,
        assignee=card.assignee,
        due_date=card.due_date,
        labels=labels_list,
        position=card.position,
        is_archived=card.is_archived,
        created_at=card.created_at,
        updated_at=card.updated_at,
        lead_id=card.lead_id,
        lead=lead_out,
        color=card.color or "yellow",
        comments=[BoardCardCommentOut.model_validate(c) for c in card.comments] if hasattr(card, 'comments') else [],
        checklist=[BoardCardChecklistOut.model_validate(c) for c in card.checklist] if hasattr(card, 'checklist') else [],
        activity=[BoardCardActivityOut.model_validate(a) for a in card.activity] if hasattr(card, 'activity') else [],
    )


@app.get("/api/boards/overview")
def get_boards_overview(show_archived: bool = Query(False), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get overview of all boards across projects"""
    query = db.query(Project)
    if show_archived:
        query = query.filter(Project.is_archived == True)
    else:
        query = query.filter(Project.is_archived == False)
    projects = query.all()
    result = []
    for p in projects:
        board = db.query(Board).filter(Board.project_id == p.id).first()
        if board:
            columns = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).all()
            cards_count = 0
            overdue_cards = []
            due_soon_cards = []
            today = datetime.now(timezone.utc).date()
            for col in columns:
                cards = db.query(BoardCard).filter(BoardCard.column_id == col.id, BoardCard.is_archived == False).all()
                cards_count += len(cards)
                for c in cards:
                    if c.due_date:
                        due = datetime.fromisoformat(c.due_date.replace('Z', '+00:00')).date()
                        if due < today:
                            overdue_cards.append(c.title)
                        elif due <= today + timedelta(days=3):
                            due_soon_cards.append(c.title)
            result.append({
                "project_id": p.id,
                "project_name": p.name,
                "board_id": board.id,
                "cards_count": cards_count,
                "columns_count": len(columns),
                "client_name": p.lead.business_name if p.lead else None,
                "overdue_cards": overdue_cards,
                "due_soon_cards": due_soon_cards,
                "color": p.color or "yellow",
                "project_lead_id": p.lead_id,
                "is_archived": p.is_archived,
            })
    return result


@app.get("/api/projects/{project_id}/board", response_model=BoardOut)
def get_project_board(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get board for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")

    board = db.query(Board).filter(Board.project_id == project_id).first()
    if not board:
        # Create board if not exists
        board = Board(id=str(uuid.uuid4()), project_id=project_id)
        db.add(board)
        db.flush()
        # Create default columns
        default_columns = [("To Do", "yellow"), ("In Progress", "blue"), ("Review", "purple"), ("Done", "green")]
        for i, (name, color) in enumerate(default_columns):
            col = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=name, position=i, color=color)
            db.add(col)
        db.commit()
        db.refresh(board)

    columns = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).order_by(BoardColumn.position).all()
    column_outs = []
    for col in columns:
        cards = db.query(BoardCard).filter(BoardCard.column_id == col.id, BoardCard.is_archived == False).order_by(BoardCard.position).all()
        card_outs = [card_to_out(c) for c in cards]
        column_outs.append(BoardColumnOut(
            id=col.id, board_id=col.board_id, name=col.name, position=col.position, color=col.color, cards=card_outs
        ))

    return BoardOut(id=board.id, project_id=board.project_id, created_at=board.created_at, color=board.color or "yellow", columns=column_outs)


@app.post("/api/boards/{board_id}/columns", response_model=BoardColumnOut, status_code=201)
def create_board_column(board_id: str, body: BoardColumnIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new column in board"""
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board tidak ditemukan")
    max_pos = db.query(BoardColumn).filter(BoardColumn.board_id == board_id).count()
    col = BoardColumn(id=str(uuid.uuid4()), board_id=board_id, name=body.name, position=body.position if body.position is not None else max_pos, color=body.color or "yellow")
    db.add(col)
    db.commit()
    db.refresh(col)
    return BoardColumnOut(id=col.id, board_id=col.board_id, name=col.name, position=col.position, color=col.color, cards=[])


@app.put("/api/board-columns/{column_id}", response_model=BoardColumnOut)
def update_board_column(column_id: str, body: BoardColumnIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update column name, position or color"""
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column tidak ditemukan")
    if body.name:
        col.name = body.name
    if body.position is not None:
        col.position = body.position
    if body.color:
        col.color = body.color
    db.commit()
    db.refresh(col)
    return BoardColumnOut(id=col.id, board_id=col.board_id, name=col.name, position=col.position, color=col.color, cards=[])


@app.delete("/api/board-columns/{column_id}", status_code=204)
def delete_board_column(column_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a column and all its cards"""
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column tidak ditemukan")
    card_ids = [c.id for c in db.query(BoardCard.id).filter(BoardCard.column_id == column_id).all()]
    if card_ids:
        db.query(BoardCardActivity).filter(BoardCardActivity.card_id.in_(card_ids)).delete(synchronize_session=False)
        db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id.in_(card_ids)).delete(synchronize_session=False)
        db.query(BoardCardComment).filter(BoardCardComment.card_id.in_(card_ids)).delete(synchronize_session=False)
    db.query(BoardCard).filter(BoardCard.column_id == column_id).delete()
    db.delete(col)
    db.commit()


@app.post("/api/board-columns/{column_id}/cards", response_model=BoardCardOut, status_code=201)
def create_board_card(column_id: str, body: BoardCardIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new card in column"""
    col = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column tidak ditemukan")
    max_pos = db.query(BoardCard).filter(BoardCard.column_id == column_id).count()
    card = BoardCard(
        id=str(uuid.uuid4()),
        column_id=column_id,
        title=body.title,
        description=body.description,
        assignee=body.assignee or current_user.name,
        due_date=body.due_date,
        labels=json.dumps(body.labels) if body.labels else None,
        position=max_pos,
        lead_id=body.lead_id,
        color=body.color or "yellow",
    )
    db.add(card)

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="created",
        description=f"Card created: {body.title}",
        actor=current_user.name,
    )
    db.add(activity)
    db.commit()
    db.refresh(card)

    return card_to_out(card)


@app.get("/api/board-cards/{card_id}", response_model=BoardCardOut)
def get_board_card(card_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get card details"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")
    return card_to_out(card)


@app.put("/api/board-cards/{card_id}", response_model=BoardCardOut)
def update_board_card(card_id: str, body: BoardCardUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update card"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    if body.title is not None:
        card.title = body.title
    if body.description is not None:
        card.description = body.description
    if body.assignee is not None:
        card.assignee = body.assignee
    if body.due_date is not None:
        card.due_date = body.due_date
    if body.labels is not None:
        card.labels = json.dumps(body.labels)
    if body.column_id is not None:
        card.column_id = body.column_id
    if body.position is not None:
        card.position = body.position
    if body.lead_id is not None:
        card.lead_id = body.lead_id
    if body.color is not None:
        card.color = body.color
    if body.is_archived is not None:
        card.is_archived = body.is_archived
        # Add activity for archive/unarchive
        action = "archived" if body.is_archived else "unarchived"
        activity = BoardCardActivity(
            id=str(uuid.uuid4()),
            card_id=card.id,
            action=action,
            description=f"Card {action}",
            actor=current_user.name,
        )
        db.add(activity)

    card.updated_at = datetime.now(timezone.utc).isoformat()

    # Add update activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="updated",
        description="Card updated",
        actor=current_user.name,
    )
    db.add(activity)

    db.commit()
    db.refresh(card)
    return card_to_out(card)


@app.delete("/api/board-cards/{card_id}", status_code=204)
def delete_board_card(card_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a card"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")
    db.query(BoardCardActivity).filter(BoardCardActivity.card_id == card_id).delete()
    db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id == card_id).delete()
    db.query(BoardCardComment).filter(BoardCardComment.card_id == card_id).delete()
    db.delete(card)
    db.commit()


@app.post("/api/board-cards/{card_id}/move", response_model=BoardCardOut)
def move_board_card(card_id: str, body: MoveCardRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Move card to another column"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    old_column = card.column_id
    card.column_id = body.column_id
    if body.position is not None:
        card.position = body.position
    else:
        max_pos = db.query(BoardCard).filter(BoardCard.column_id == body.column_id).count()
        card.position = max_pos

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card.id,
        action="moved",
        description=f"Card moved to another column",
        actor=current_user.name,
    )
    db.add(activity)

    db.commit()
    db.refresh(card)
    return card_to_out(card)


@app.post("/api/board-cards/{card_id}/comments", response_model=BoardCardCommentOut, status_code=201)
def create_card_comment(card_id: str, body: BoardCardCommentIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add comment to card"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    comment = BoardCardComment(
        id=str(uuid.uuid4()),
        card_id=card_id,
        author=current_user.name,
        content=body.content,
    )
    db.add(comment)

    # Add activity
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="commented",
        description=f"Comment added: {body.content[:50]}...",
        actor=current_user.name,
    )
    db.add(activity)
    db.commit()
    db.refresh(comment)
    return comment


@app.post("/api/board-cards/{card_id}/checklist", response_model=BoardCardChecklistOut, status_code=201)
def create_card_checklist(card_id: str, body: BoardCardChecklistIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Add checklist item to card"""
    card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card tidak ditemukan")

    max_pos = db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id == card_id).count()
    item = BoardCardChecklist(
        id=str(uuid.uuid4()),
        card_id=card_id,
        text=body.text,
        position=max_pos,
    )
    db.add(item)
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="checklist",
        description=f'Checklist "{body.text}" ditambahkan',
        actor=current_user.name,
    )
    db.add(activity)
    db.commit()
    db.refresh(item)
    return item


@app.patch("/api/board-cards/{card_id}/checklist/{item_id}", response_model=BoardCardChecklistOut)
def update_card_checklist(card_id: str, item_id: str, is_done: bool = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle checklist item"""
    item = db.query(BoardCardChecklist).filter(BoardCardChecklist.id == item_id, BoardCardChecklist.card_id == card_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item tidak ditemukan")
    item.is_done = is_done
    status_text = "selesai" if is_done else "belum selesai"
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="checklist",
        description=f'Checklist "{item.text}" ditandai {status_text}',
        actor=current_user.name,
    )
    db.add(activity)
    db.commit()
    db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Client Notes
# ---------------------------------------------------------------------------

@app.get("/api/client-notes", response_model=list[ClientNoteOut])
def get_client_notes(
    lead_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(ClientNote).filter(ClientNote.lead_id == lead_id).order_by(ClientNote.id.desc()).all()


@app.post("/api/client-notes", response_model=ClientNoteOut, status_code=201)
def create_client_note(body: ClientNoteIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.category not in ("BISNIS", "TEKNIS", "PENTING"):
        raise HTTPException(status_code=400, detail="Category harus 'BISNIS', 'TEKNIS', atau 'PENTING'")
    note = ClientNote(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=current_user.name,
        category=body.category,
        content=body.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.delete("/api/client-notes/{note_id}", status_code=204)
def delete_client_note(note_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.query(ClientNote).filter(ClientNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note tidak ditemukan")
    db.delete(note)
    db.commit()


@app.get("/api/clients/notes/{client_id}", response_model=list[ClientNoteOut])
def get_client_notes_by_path(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ClientNote).filter(ClientNote.lead_id == client_id).order_by(ClientNote.id.desc()).all()


@app.post("/api/clients/notes", response_model=ClientNoteOut, status_code=201)
def create_client_note_alias(body: ClientNoteIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.category not in ("BISNIS", "TEKNIS", "PENTING"):
        raise HTTPException(status_code=400, detail="Category harus 'BISNIS', 'TEKNIS', atau 'PENTING'")
    note = ClientNote(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=current_user.name,
        category=body.category,
        content=body.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


# ---------------------------------------------------------------------------
# Credentials Vault (Encrypted)
# ---------------------------------------------------------------------------

@app.get("/api/credentials", response_model=list[CredentialOut])
def get_credentials(
    lead_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ClientCredential)
    if lead_id == "internal":
        query = query.filter(ClientCredential.lead_id.is_(None))
    elif lead_id:
        query = query.filter(ClientCredential.lead_id == int(lead_id))
    creds = query.order_by(ClientCredential.created_at.desc()).all()
    results = []
    for c in creds:
        raw_fields = json.loads(c.fields) if c.fields else []
        decrypted_fields = []
        for f in raw_fields:
            val = f["value"]
            if f.get("is_secret"):
                try:
                    val = decrypt_password(val)
                except Exception:
                    val = "***decryption_error***"
            decrypted_fields.append(CredentialFieldOut(key=f["key"], value=val, is_secret=f.get("is_secret", False)))
        results.append(CredentialOut(
            id=c.id, lead_id=c.lead_id, category=c.category, title=c.title,
            fields=decrypted_fields, created_at=c.created_at,
        ))
    return results


@app.post("/api/credentials", response_model=CredentialOut, status_code=201)
def create_credential(body: CredentialIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stored_fields = []
    for f in body.fields:
        val = encrypt_password(f.value) if f.is_secret else f.value
        stored_fields.append({"key": f.key, "value": val, "is_secret": f.is_secret})
    cred = ClientCredential(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        category=body.category,
        title=body.title,
        fields=json.dumps(stored_fields),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    log_audit(db, current_user.name, "CREATE", "client_credentials", cred.id, {"title": body.title, "category": body.category})
    out_fields = [CredentialFieldOut(key=f.key, value=f.value, is_secret=f.is_secret) for f in body.fields]
    return CredentialOut(
        id=cred.id, lead_id=cred.lead_id, category=cred.category, title=cred.title,
        fields=out_fields, created_at=cred.created_at,
    )


@app.put("/api/credentials/{cred_id}", response_model=CredentialOut)
def update_credential(cred_id: str, body: CredentialUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cred = db.query(ClientCredential).filter(ClientCredential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential tidak ditemukan")
    if body.category is not None:
        cred.category = body.category
    if body.title is not None:
        cred.title = body.title
    if body.fields is not None:
        stored_fields = []
        for f in body.fields:
            val = encrypt_password(f.value) if f.is_secret else f.value
            stored_fields.append({"key": f.key, "value": val, "is_secret": f.is_secret})
        cred.fields = json.dumps(stored_fields)
    db.commit()
    db.refresh(cred)
    raw_fields = json.loads(cred.fields) if cred.fields else []
    out_fields = []
    for f in raw_fields:
        val = f["value"]
        if f.get("is_secret"):
            try:
                val = decrypt_password(val)
            except Exception:
                val = "***decryption_error***"
        out_fields.append(CredentialFieldOut(key=f["key"], value=val, is_secret=f.get("is_secret", False)))
    log_audit(db, current_user.name, "UPDATE", "client_credentials", cred_id, {"title": cred.title})
    return CredentialOut(
        id=cred.id, lead_id=cred.lead_id, category=cred.category, title=cred.title,
        fields=out_fields, created_at=cred.created_at,
    )


@app.delete("/api/credentials/{cred_id}", status_code=204)
def delete_credential(cred_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cred = db.query(ClientCredential).filter(ClientCredential.id == cred_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential tidak ditemukan")
    log_audit(db, current_user.name, "DELETE", "client_credentials", cred_id, {"title": cred.title})
    db.delete(cred)
    db.commit()


# ---------------------------------------------------------------------------
# Credential Categories Management
# ---------------------------------------------------------------------------

@app.get("/api/credential-categories")
def get_credential_categories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="credential_categories").first()
    if row and row.value:
        return json.loads(row.value)
    return ["WordPress", "Google Account", "Sosmed", "Server", "Email", "Hosting", "Domain", "Analytics"]


@app.put("/api/credential-categories")
def update_credential_categories(categories: list[str], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="credential_categories").first()
    if row:
        row.value = json.dumps(categories)
    else:
        db.add(SystemSettings(key="credential_categories", value=json.dumps(categories)))
    db.commit()
    return categories


# ---------------------------------------------------------------------------
# Client Documents (Cloud Links)
# ---------------------------------------------------------------------------

@app.get("/api/documents", response_model=list[DocumentOut])
def get_documents(
    lead_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ClientDocument)
    if lead_id == "internal":
        query = query.filter(ClientDocument.lead_id.is_(None))
    elif lead_id:
        query = query.filter(ClientDocument.lead_id == int(lead_id))
    return query.order_by(ClientDocument.created_at.desc()).all()


@app.post("/api/documents", response_model=DocumentOut, status_code=201)
def create_document(body: DocumentIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = ClientDocument(
        id=str(uuid.uuid4()),
        lead_id=body.lead_id,
        title=body.title,
        cloud_url=body.cloud_url,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    log_audit(db, current_user.name, "CREATE", "client_documents", doc.id, {"title": body.title})
    return doc


@app.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(ClientDocument).filter(ClientDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    log_audit(db, current_user.name, "DELETE", "client_documents", doc_id, {"title": doc.title})
    db.delete(doc)
    db.commit()


# ---------------------------------------------------------------------------
# Ads Tracking Center
# ---------------------------------------------------------------------------

class AdsCampaignIn(BaseModel):
    name: str
    target_audience: str
    budget: float
    drive_link: Optional[str] = None
    status: str = "PLANNING"


class AdsCampaignUpdate(BaseModel):
    name: Optional[str] = None
    target_audience: Optional[str] = None
    budget: Optional[float] = None
    drive_link: Optional[str] = None
    leads_count: Optional[int] = None
    conversions_count: Optional[int] = None
    status: Optional[str] = None


class AdsCampaignOut(BaseModel):
    id: str
    name: str
    target_audience: str
    budget: float
    drive_link: Optional[str] = None
    leads_count: int
    conversions_count: int
    status: str
    created_at: str
    cac: Optional[float] = None
    cost_per_lead: Optional[float] = None
    model_config = {"from_attributes": True}


def _ads_out(c: AdsCampaign) -> AdsCampaignOut:
    cac = (c.budget / c.conversions_count) if c.conversions_count and c.conversions_count > 0 else None
    cpl = (c.budget / c.leads_count) if c.leads_count and c.leads_count > 0 else None
    return AdsCampaignOut(
        id=c.id, name=c.name, target_audience=c.target_audience, budget=c.budget,
        drive_link=c.drive_link, leads_count=c.leads_count or 0, conversions_count=c.conversions_count or 0,
        status=c.status, created_at=c.created_at, cac=cac, cost_per_lead=cpl,
    )


@app.get("/api/ads/campaigns", response_model=list[AdsCampaignOut])
def get_ads_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaigns = db.query(AdsCampaign).order_by(AdsCampaign.created_at.desc()).all()
    return [_ads_out(c) for c in campaigns]


@app.post("/api/ads/campaigns", response_model=AdsCampaignOut, status_code=201)
def create_ads_campaign(body: AdsCampaignIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = AdsCampaign(
        id=str(uuid.uuid4()),
        name=body.name,
        target_audience=body.target_audience,
        budget=body.budget,
        drive_link=body.drive_link,
        status=body.status,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    if body.status == "ACTIVE" and body.budget > 0:
        ads_wallet = db.query(Wallet).filter(Wallet.name == "Dompet Budget Ads").first()
        if not ads_wallet:
            ads_wallet = Wallet(name="Dompet Budget Ads", balance=0, icon="📢", color="#f59e0b")
            db.add(ads_wallet)
            db.commit()
            db.refresh(ads_wallet)
        txn = Transaction(
            wallet_id=ads_wallet.id,
            type="expense",
            amount=body.budget,
            category="Ads Campaign",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            notes=f"Budget iklan: {body.name}",
            is_billed=False,
            is_archived=False,
        )
        db.add(txn)
        ads_wallet.balance -= body.budget
        db.commit()

    log_audit(db, current_user.name, "CREATE", "ads_campaigns", campaign.id, {"name": body.name})
    return _ads_out(campaign)


@app.put("/api/ads/campaigns/{campaign_id}", response_model=AdsCampaignOut)
def update_ads_campaign(campaign_id: str, body: AdsCampaignUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(AdsCampaign).filter(AdsCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")

    old_status = campaign.status

    if body.name is not None:
        campaign.name = body.name
    if body.target_audience is not None:
        campaign.target_audience = body.target_audience
    if body.budget is not None:
        campaign.budget = body.budget
    if body.drive_link is not None:
        campaign.drive_link = body.drive_link
    if body.leads_count is not None:
        campaign.leads_count = body.leads_count
    if body.conversions_count is not None:
        campaign.conversions_count = body.conversions_count
    if body.status is not None:
        campaign.status = body.status

    if old_status == "PLANNING" and body.status == "ACTIVE" and campaign.budget > 0:
        ads_wallet = db.query(Wallet).filter(Wallet.name == "Dompet Budget Ads").first()
        if not ads_wallet:
            ads_wallet = Wallet(name="Dompet Budget Ads", balance=0, icon="📢", color="#f59e0b")
            db.add(ads_wallet)
            db.commit()
            db.refresh(ads_wallet)
        txn = Transaction(
            wallet_id=ads_wallet.id,
            type="expense",
            amount=campaign.budget,
            category="Ads Campaign",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            notes=f"Budget iklan: {campaign.name}",
            is_billed=False,
            is_archived=False,
        )
        db.add(txn)
        ads_wallet.balance -= campaign.budget
        db.commit()

    db.commit()
    db.refresh(campaign)
    log_audit(db, current_user.name, "UPDATE", "ads_campaigns", campaign_id, {"name": campaign.name})
    return _ads_out(campaign)


@app.delete("/api/ads/campaigns/{campaign_id}", status_code=204)
def delete_ads_campaign(campaign_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(AdsCampaign).filter(AdsCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")
    log_audit(db, current_user.name, "DELETE", "ads_campaigns", campaign_id, {"name": campaign.name})
    db.delete(campaign)
    db.commit()


# ---------------------------------------------------------------------------
# Content Planner & Google Calendar Integration
# ---------------------------------------------------------------------------

GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")


def _get_setting(key: str, default: str = "") -> str:
    db = SessionLocal()
    try:
        row = db.query(SystemSettings).filter_by(key=key).first()
        return row.value if row and row.value else default
    finally:
        db.close()


def _get_google_calendar_service():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/calendar"]

        sa_json = _get_setting("google_service_account_json", GOOGLE_SERVICE_ACCOUNT_JSON)
        if sa_json:
            import json as _json
            info = _json.loads(sa_json)
            credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        elif GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
            credentials = service_account.Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes)
        else:
            return None

        return build("calendar", "v3", credentials=credentials)
    except Exception:
        return None


def sync_to_google_calendar(title: str, date: str, event_id: str | None = None) -> str | None:
    service = _get_google_calendar_service()
    if not service:
        return event_id

    calendar_id = _get_setting("google_calendar_id", GOOGLE_CALENDAR_ID)

    event_body = {
        "summary": title,
        "start": {"date": date},
        "end": {"date": date},
    }

    try:
        if event_id:
            service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
            return event_id
        else:
            result = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            return result.get("id")
    except Exception:
        return event_id


@app.get("/api/content-types")
def get_content_types(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="content_types").first()
    if row and row.value:
        return json.loads(row.value)
    return [
        {"value": "IG_CAROUSEL", "label": "IG Carousel", "color": "#f97316"},
        {"value": "IG_REELS", "label": "IG Reels", "color": "#ec4899"},
        {"value": "SEO_ARTICLE", "label": "Artikel SEO", "color": "#10b981"},
        {"value": "TIKTOK", "label": "TikTok", "color": "#06b6d4"},
        {"value": "YOUTUBE", "label": "YouTube", "color": "#ef4444"},
    ]


@app.put("/api/content-types")
def update_content_types(types: list[dict], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(SystemSettings).filter_by(key="content_types").first()
    if row:
        row.value = json.dumps(types)
    else:
        db.add(SystemSettings(key="content_types", value=json.dumps(types)))
    db.commit()
    return types


class ContentScheduleIn(BaseModel):
    title: str
    type: str
    schedule_date: str
    status: str = "DRAFT"


class ContentScheduleUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    schedule_date: Optional[str] = None
    status: Optional[str] = None


class ContentScheduleOut(BaseModel):
    id: str
    title: str
    type: str
    schedule_date: str
    google_event_id: Optional[str] = None
    status: str
    created_at: str
    model_config = {"from_attributes": True}


@app.get("/api/content-schedule", response_model=list[ContentScheduleOut])
def get_content_schedules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ContentSchedule).order_by(ContentSchedule.schedule_date.asc()).all()


@app.post("/api/content-schedule", response_model=ContentScheduleOut, status_code=201)
def create_content_schedule(body: ContentScheduleIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    google_event_id = sync_to_google_calendar(body.title, body.schedule_date)

    schedule = ContentSchedule(
        id=str(uuid.uuid4()),
        title=body.title,
        type=body.type,
        schedule_date=body.schedule_date,
        google_event_id=google_event_id,
        status=body.status,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    log_audit(db, current_user.name, "CREATE", "content_schedules", schedule.id, {"title": body.title})
    return schedule


@app.put("/api/content-schedule/{schedule_id}", response_model=ContentScheduleOut)
def update_content_schedule(schedule_id: str, body: ContentScheduleUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    schedule = db.query(ContentSchedule).filter(ContentSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")

    if body.title is not None:
        schedule.title = body.title
    if body.type is not None:
        schedule.type = body.type
    if body.schedule_date is not None:
        schedule.schedule_date = body.schedule_date
    if body.status is not None:
        schedule.status = body.status

    db.commit()
    db.refresh(schedule)

    sync_to_google_calendar(schedule.title, schedule.schedule_date, schedule.google_event_id)

    log_audit(db, current_user.name, "UPDATE", "content_schedules", schedule_id, {"title": schedule.title})
    return schedule


@app.delete("/api/content-schedule/{schedule_id}", status_code=204)
def delete_content_schedule(schedule_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    schedule = db.query(ContentSchedule).filter(ContentSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")

    if schedule.google_event_id:
        service = _get_google_calendar_service()
        if service:
            try:
                service.events().delete(calendarId=GOOGLE_CALENDAR_ID, eventId=schedule.google_event_id).execute()
            except Exception:
                pass

    log_audit(db, current_user.name, "DELETE", "content_schedules", schedule_id, {"title": schedule.title})
    db.delete(schedule)
    db.commit()


# ---------------------------------------------------------------------------
# Bulk Outreach Scheduler (Blast Campaign)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Provider Config & Outreach Costs API
# ---------------------------------------------------------------------------

class ProviderConfigOut(BaseModel):
    id: str
    provider_name: str
    remaining_quota: float
    price_per_unit_idr: float
    price_input_token_usd: float
    price_output_token_usd: float
    model_config = {"from_attributes": True}


@app.get("/api/provider-configs", response_model=list[ProviderConfigOut])
def get_provider_configs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ProviderConfig).all()


@app.put("/api/provider-configs/{provider_id}")
def update_provider_config(provider_id: str, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    provider = db.query(ProviderConfig).filter_by(id=provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    if "remaining_quota" in body:
        provider.remaining_quota = body["remaining_quota"]
    if "price_per_unit_idr" in body:
        provider.price_per_unit_idr = body["price_per_unit_idr"]
    if "price_input_token_usd" in body:
        provider.price_input_token_usd = body["price_input_token_usd"]
    if "price_output_token_usd" in body:
        provider.price_output_token_usd = body["price_output_token_usd"]
    db.commit()
    return {"ok": True}


@app.get("/api/finance/outreach-costs")
def get_outreach_costs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    providers = db.query(ProviderConfig).all()
    provider_list = []
    for p in providers:
        cost_per_unit_idr = p.price_per_unit_idr if p.price_per_unit_idr else (
            ((p.price_input_token_usd + p.price_output_token_usd) / 2) * 1000 * USD_TO_IDR
        )
        provider_list.append({
            "id": p.id,
            "provider_name": p.provider_name,
            "remaining_quota": p.remaining_quota,
            "price_per_unit_idr": p.price_per_unit_idr,
            "price_input_token_usd": p.price_input_token_usd,
            "price_output_token_usd": p.price_output_token_usd,
            "estimated_balance_idr": p.remaining_quota * cost_per_unit_idr if cost_per_unit_idr else 0,
        })

    campaigns = db.query(BlastCampaign).order_by(BlastCampaign.created_at.desc()).all()
    campaign_list = []
    for c in campaigns:
        cost = c.total_operational_cost_idr or 0
        conversions = c.converted_clients_count or 0
        cpa = cost / conversions if conversions > 0 else None
        revenue_estimate = conversions * 5000000
        roi = ((revenue_estimate - cost) / cost * 100) if cost > 0 else None
        campaign_list.append({
            "id": c.id,
            "name": c.name,
            "created_at": c.created_at,
            "sent_count": c.sent_count or 0,
            "total_operational_cost_idr": cost,
            "converted_clients_count": conversions,
            "cpa": cpa,
            "roi": roi,
            "status": c.status,
        })

    return {"providers": provider_list, "campaigns": campaign_list}


@app.put("/api/blast-campaigns/{campaign_id}/conversions")
def update_blast_conversions(campaign_id: str, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")
    if "converted_clients_count" in body:
        campaign.converted_clients_count = body["converted_clients_count"]
    db.commit()
    return {"ok": True}


class BlastCampaignIn(BaseModel):
    name: str
    template_id: Optional[str] = None
    filter_criteria: dict
    scheduled_for: str


class BlastCampaignOut(BaseModel):
    id: str
    name: str
    template_id: Optional[str] = None
    filter_criteria: dict
    scheduled_for: str
    status: str
    sent_count: int
    failed_count: int
    created_at: str
    model_config = {"from_attributes": True}


@app.get("/api/campaign/blast/schedule", response_model=list[BlastCampaignOut])
def get_blast_campaigns(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaigns = db.query(BlastCampaign).order_by(BlastCampaign.created_at.desc()).all()
    results = []
    for c in campaigns:
        results.append(BlastCampaignOut(
            id=c.id, name=c.name, template_id=c.template_id,
            filter_criteria=json.loads(c.filter_criteria) if c.filter_criteria else {},
            scheduled_for=c.scheduled_for, status=c.status,
            sent_count=c.sent_count or 0, failed_count=c.failed_count or 0,
            created_at=c.created_at,
        ))
    return results


@app.post("/api/campaign/blast/schedule", response_model=BlastCampaignOut, status_code=201)
def create_blast_campaign(body: BlastCampaignIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = BlastCampaign(
        id=str(uuid.uuid4()),
        name=body.name,
        template_id=body.template_id,
        filter_criteria=json.dumps(body.filter_criteria),
        scheduled_for=body.scheduled_for,
        status="PENDING",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    log_audit(db, current_user.name, "CREATE", "blast_campaigns", campaign.id, {"name": body.name, "scheduled_for": body.scheduled_for})
    return BlastCampaignOut(
        id=campaign.id, name=campaign.name, template_id=campaign.template_id,
        filter_criteria=body.filter_criteria, scheduled_for=campaign.scheduled_for,
        status=campaign.status, sent_count=0, failed_count=0, created_at=campaign.created_at,
    )


@app.delete("/api/campaign/blast/schedule/{campaign_id}", status_code=204)
def delete_blast_campaign(campaign_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaign = db.query(BlastCampaign).filter(BlastCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")
    log_audit(db, current_user.name, "DELETE", "blast_campaigns", campaign_id, {"name": campaign.name})
    db.delete(campaign)
    db.commit()


# ---------------------------------------------------------------------------
# APScheduler: Process pending blast campaigns
# ---------------------------------------------------------------------------

async def process_pending_blasts():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).isoformat()
        pending = db.query(BlastCampaign).filter(
            BlastCampaign.status == "PENDING",
            BlastCampaign.scheduled_for <= now,
        ).all()

        for campaign in pending:
            campaign.status = "PROCESSING"
            db.commit()

            try:
                criteria = json.loads(campaign.filter_criteria) if campaign.filter_criteria else {}
                query = db.query(Lead).filter(Lead.is_archived == False)

                if criteria.get("status"):
                    query = query.filter(Lead.status == criteria["status"])
                if criteria.get("batch_name"):
                    query = query.filter(Lead.batch_name == criteria["batch_name"])
                if criteria.get("min_rating") and int(criteria["min_rating"]) > 0:
                    query = query.filter(Lead.rating >= int(criteria["min_rating"]))

                leads = query.all()
                token = get_fonnte_token(db)

                template = None
                if campaign.template_id:
                    template = db.query(DynamicTemplate).filter(DynamicTemplate.id == campaign.template_id).first()

                if not template:
                    templates = db.query(DynamicTemplate).filter(
                        DynamicTemplate.type == "WA_BLAST",
                        DynamicTemplate.is_active == True,
                    ).all()
                    if templates:
                        template = random.choice(templates)

                sent = 0
                failed = 0
                for lead in leads:
                    frontend_url = _get_setting("frontend_url", os.environ["FRONTEND_URL"])
                    report_slug = generate_report_for_lead(lead, db)
                    report_link = f"{FRONTEND_URL}/r/{report_slug}"

                    if template:
                        message = template.content.replace("{{client_name}}", lead.business_name).replace("{{business_name}}", lead.business_name)
                    else:
                        message = f"Halo {lead.business_name}, kami dari Kantor Teman ingin menawarkan layanan kami.\n\nLihat laporan audit digital Anda di sini: {report_link}"

                    message = message.replace("{{proposal_link}}", f"\n{report_link}\n")

                    success = await send_fonnte_message(lead.phone_number, message, token)
                    if success:
                        lead.status = "Contacted"
                        sent += 1
                    else:
                        failed += 1
                    db.commit()
                    await asyncio.sleep(5)

                campaign.sent_count = sent
                campaign.failed_count = failed
                campaign.status = "SUCCESS"
                log_outreach_cost(db, campaign.id, sent)
                db.commit()
            except Exception:
                campaign.status = "FAILED"
                db.commit()
    finally:
        db.close()


from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.schedulers.outreach_machine import process_outreach_lifecycle_states


async def scheduled_followup_processor():
    db = SessionLocal()
    try:
        enabled = db.query(SystemSettings).filter_by(key="followup_enabled").first()
        if not enabled or enabled.value != "true":
            return

        hour_setting = db.query(SystemSettings).filter_by(key="followup_hour").first()
        target_hour = int(hour_setting.value) if hour_setting and hour_setting.value else 9
        current_hour = datetime.now(timezone.utc).hour + 7
        if current_hour >= 24:
            current_hour -= 24
        if current_hour != target_hour:
            return

        now = datetime.now(timezone.utc)
        sequences = db.query(FollowUpSequence).filter(
            FollowUpSequence.status == "ACTIVE",
            FollowUpSequence.next_send_at <= now.isoformat(),
        ).all()

        token = get_fonnte_token(db)

        for seq in sequences:
            lead = db.query(Lead).filter(Lead.id == seq.lead_id).first()
            if not lead:
                seq.status = "STOPPED"
                seq.stopped_reason = "lead_not_found"
                db.commit()
                continue

            template_ids = json.loads(seq.template_ids) if seq.template_ids else []
            delays = json.loads(seq.delays) if seq.delays else []

            if seq.current_step >= len(delays):
                seq.status = "COMPLETED"
                db.commit()
                continue

            message = None
            if template_ids and seq.current_step < len(template_ids):
                tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == template_ids[seq.current_step]).first()
                if tmpl:
                    message = tmpl.content.replace("{{business_name}}", lead.business_name).replace("{{client_name}}", lead.business_name)

            if not message:
                followup_defaults = [
                    f"Halo {lead.business_name}, saya ingin follow up terkait laporan audit digital yang sudah saya kirimkan sebelumnya. Apakah ada pertanyaan yang bisa saya bantu jawab?",
                    f"Pak, saya notice laporan audit untuk {lead.business_name} sudah dibuka tapi belum ada respons. Apakah ada kendala atau pertanyaan? Saya siap bantu jelaskan lebih detail.",
                    f"Halo Pak, ini follow up terakhir dari saya untuk {lead.business_name}. Jika memang belum berminat saat ini, tidak masalah. Tapi perlu diingat, slot optimasi wilayah Anda terbatas dan kompetitor terus bergerak.",
                ]
                message = followup_defaults[min(seq.current_step, len(followup_defaults) - 1)]

            await send_fonnte_message(lead.phone_number, message, token)

            seq.current_step += 1
            if seq.current_step >= len(delays):
                seq.status = "COMPLETED"
                seq.next_send_at = None
            else:
                next_delay = delays[seq.current_step] if seq.current_step < len(delays) else 7
                seq.next_send_at = (now + timedelta(days=next_delay)).isoformat()
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# AI Chat Schemas (Semuts.sh Integration)
# ---------------------------------------------------------------------------

class ChatProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    default_model: Optional[str] = "glm-5"
    context_window_size: Optional[int] = 20


class ChatProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    default_model: Optional[str] = None
    context_window_size: Optional[int] = None


class ChatProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    default_model: str
    context_window_size: int
    created_at: str
    updated_at: Optional[str]
    model_config = {"from_attributes": True}


class ChatConversationCreate(BaseModel):
    project_id: str
    title: Optional[str] = "New Chat"


class ChatConversationUpdate(BaseModel):
    title: Optional[str] = None


class ChatConversationOut(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: str
    updated_at: Optional[str]
    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    tokens_used: int
    model_used: Optional[str]
    created_at: str
    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    agent_mode: Optional[bool] = False  # Enable tool use


class ChatMemoryCreate(BaseModel):
    content: str


class ChatMemoryOut(BaseModel):
    id: str
    project_id: str
    content: str
    pinned_by: int
    created_at: str
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Content Generator Schemas
# ---------------------------------------------------------------------------

class AIProxyIn(BaseModel):
    name: str
    base_url: str
    api_key: str = ""
    model: str = ""

class AIProxyOut(BaseModel):
    id: str
    name: str
    base_url: str
    api_key: str = ""
    model: str = ""
    is_active: bool
    created_at: str
    model_config = {"from_attributes": True}

class ContentProviderIn(BaseModel):
    name: str
    tool_type: str = "image"
    base_url: str
    api_key: Optional[str] = None
    model: str
    extra_params: Optional[dict] = None
    is_active: bool = True

class ContentProviderOut(BaseModel):
    id: str
    name: str
    tool_type: str
    base_url: str
    api_key: Optional[str] = None
    model: str
    extra_params: Optional[Any] = None
    is_active: bool
    created_at: str
    model_config = {"from_attributes": True}

class ContentSessionIn(BaseModel):
    name: str
    description: Optional[str] = None

class ContentSessionUpdate(BaseModel):
    name: str
    description: Optional[str] = None

class ContentSessionOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    model_config = {"from_attributes": True}

class ContentGenerationOut(BaseModel):
    id: str
    session_id: Optional[str] = None
    tool_type: str
    input_data: Any = {}
    output_data: Optional[Any] = None
    model_used: Optional[str] = None
    provider_name: Optional[str] = None
    status: str
    error_msg: Optional[str] = None
    created_at: str
    model_config = {"from_attributes": True}

class ImageGenRequest(BaseModel):
    prompt: str
    provider_id: str
    session_id: Optional[str] = None
    negative_prompt: Optional[str] = None
    width: Optional[int] = 512
    height: Optional[int] = 512

class CaptionGenRequest(BaseModel):
    topic: str
    platform: str = "instagram"
    tone: Optional[str] = "casual"
    keywords: Optional[List[str]] = []
    session_id: Optional[str] = None
    context_from: Optional[List[str]] = []

class SeoArticleGenRequest(BaseModel):
    keyword: str
    title: Optional[str] = None
    word_count: Optional[int] = 800
    tone: Optional[str] = "informatif"
    search_intent: Optional[str] = "informational"
    # Semrush data
    keyword_difficulty: Optional[int] = None
    search_volume: Optional[int] = None
    lsi_keywords: Optional[List[str]] = []
    # Content structure
    faq_topics: Optional[List[str]] = []
    serp_features: Optional[List[str]] = []
    # Context
    target_audience: Optional[str] = None
    target_location: Optional[str] = None
    brand_name: Optional[str] = None
    unique_angle: Optional[str] = None
    internal_link_targets: Optional[str] = None
    session_id: Optional[str] = None
    context_from: Optional[List[str]] = []


# ---------------------------------------------------------------------------
# Agent Tools - Functions AI can execute
# ---------------------------------------------------------------------------

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_lead",
            "description": "Buat lead baru. WAJIB panggil untuk menambah klien/prospek baru.",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_name": {"type": "string", "description": "Nama bisnis/klien"},
                    "phone_number": {"type": "string", "description": "Nomor telepon/WhatsApp"},
                    "address": {"type": "string", "description": "Alamat (opsional)"},
                    "product_interest": {"type": "string", "description": "Produk yang diminati (opsional)"}
                },
                "required": ["business_name", "phone_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_leads",
            "description": "Cari leads/klien. WAJIB panggil tool ini untuk query data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "business_name": {"type": "string", "description": "Filter by business name (partial match)"},
                    "status": {"type": "string", "description": "Filter by status", "enum": ["Scraped", "Contacted", "Replied", "Closed", "Closed/Client"]},
                    "product_interest": {"type": "string", "description": "Filter by product interest"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lead_details",
            "description": "Ambil detail lead termasuk proyeknya. WAJIB panggil untuk lihat detail klien.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID lead"},
                    "business_name": {"type": "string", "description": "Nama bisnis untuk konfirmasi"}
                },
                "required": ["lead_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_client_projects",
            "description": "List proyek klien. WAJIB panggil untuk lihat proyek berjalan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID lead/klien"}
                },
                "required": ["lead_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_project",
            "description": "Update proyek (harga, status). WAJIB panggil untuk update proyek klien.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "ID proyek"},
                    "business_name": {"type": "string", "description": "Nama bisnis untuk konfirmasi"},
                    "nominal": {"type": "number", "description": "Nominal baru (harga bulanan/total)"},
                    "status": {"type": "string", "description": "Status: ACTIVE, COMPLETED, HOLD"}
                },
                "required": ["project_id", "business_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_lead_status",
            "description": "Update status lead. WAJIB panggil untuk ubah status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID lead"},
                    "business_name": {"type": "string", "description": "Nama bisnis untuk konfirmasi"},
                    "status": {"type": "string", "description": "Status baru", "enum": ["Scraped", "Contacted", "Replied", "Closed", "Closed/Client"]}
                },
                "required": ["lead_id", "business_name", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp",
            "description": "Kirim WA ke lead. PANGGIL SETELAH create_proposal untuk dapat proposal_link. WAJIB sertakan proposal_link di replacements jika pakai template dengan placeholder {{proposal_link}}.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID lead"},
                    "business_name": {"type": "string", "description": "Nama bisnis untuk konfirmasi"},
                    "message": {"type": "string", "description": "Isi pesan (opsional jika pakai template_id)"},
                    "template_id": {"type": "string", "description": "ID template WA_BLAST dari database"},
                    "replacements": {"type": "object", "description": "WAJIB isi proposal_link dari hasil create_proposal. Contoh: {\"proposal_link\": \"https://...\"}"}
                },
                "required": ["lead_id", "business_name", "template_id", "replacements"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_wa_templates",
            "description": "List semua template WA_BLAST yang aktif. WAJIB panggil sebelum send_whatsapp untuk lihat template tersedia.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_products",
            "description": "List semua produk dengan info retainer/one-time. WAJIB panggil sebelum create_proposal.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_summary",
            "description": "Ringkasan bisnis. WAJIB panggil untuk overview.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_proposal",
            "description": "Buat proposal. WAJIB panggil untuk buat penawaran baru.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "ID lead"},
                    "business_name": {"type": "string", "description": "Nama bisnis untuk konfirmasi"},
                    "services": {"type": "string", "description": "JSON array: [{\"name\": \"...\", \"price\": 0, \"is_retainer\": false, \"features\": []}]"}
                },
                "required": ["lead_id", "business_name", "services"]
            }
        }
    }
]


def execute_tool_call(tool_name: str, tool_args: dict, db: Session, current_user: User) -> dict:
    """Execute a tool call and return the result."""
    try:
        if tool_name == "create_lead":
            # Check if lead with same phone already exists
            existing = db.query(Lead).filter(Lead.phone_number == tool_args["phone_number"]).first()
            if existing:
                return {"success": False, "error": f"Lead dengan nomor {tool_args['phone_number']} sudah ada: {existing.business_name} (ID: {existing.id})"}
            lead = Lead(
                business_name=tool_args["business_name"],
                phone_number=tool_args["phone_number"],
                address=tool_args.get("address", ""),
                product_interest=tool_args.get("product_interest"),
                status="Scraped",
                lead_score=50,
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
            log_audit(db, current_user.name, "CREATE", "leads", lead.id, {"business_name": lead.business_name, "phone": lead.phone_number})
            return {"success": True, "result": {"lead_id": lead.id, "business_name": lead.business_name, "phone_number": lead.phone_number, "status": lead.status}}

        elif tool_name == "search_leads":
            query = db.query(Lead).filter(Lead.is_archived == False)
            if tool_args.get("business_name"):
                query = query.filter(Lead.business_name.ilike(f"%{tool_args['business_name']}%"))
            if tool_args.get("status"):
                query = query.filter(Lead.status == tool_args["status"])
            if tool_args.get("product_interest"):
                query = query.filter(Lead.product_interest.ilike(f"%{tool_args['product_interest']}%"))
            limit = tool_args.get("limit", 10)
            leads = query.order_by(Lead.lead_score.desc()).limit(limit).all()
            return {
                "success": True,
                "result": [{
                    "id": l.id,
                    "business_name": l.business_name,
                    "phone_number": l.phone_number,
                    "status": l.status,
                    "product_interest": l.product_interest,
                    "lead_score": l.lead_score,
                } for l in leads],
                "count": len(leads)
            }

        elif tool_name == "update_lead_status":
            lead = db.query(Lead).filter(Lead.id == tool_args["lead_id"]).first()
            if not lead:
                return {"success": False, "error": f"Lead ID {tool_args.get('lead_id')} tidak ditemukan"}
            # Validate business_name if provided
            if tool_args.get("business_name") and tool_args["business_name"].lower() not in lead.business_name.lower():
                return {"success": False, "error": f"Konfirmasi gagal: lead ID {lead.id} adalah '{lead.business_name}', bukan '{tool_args['business_name']}'"}
            old_status = lead.status
            lead.status = tool_args["status"]
            db.commit()
            log_audit(db, current_user.name, "UPDATE", "leads", lead.id, {"field": "status", "old": old_status, "new": tool_args["status"]})
            return {"success": True, "result": {"lead_id": lead.id, "business_name": lead.business_name, "status": tool_args["status"]}}

        elif tool_name == "send_whatsapp":
            lead = db.query(Lead).filter(Lead.id == tool_args["lead_id"]).first()
            if not lead:
                return {"success": False, "error": f"Lead ID {tool_args.get('lead_id')} tidak ditemukan"}
            # Validate business_name if provided
            if tool_args.get("business_name") and tool_args["business_name"].lower() not in lead.business_name.lower():
                return {"success": False, "error": f"Konfirmasi gagal: lead ID {lead.id} adalah '{lead.business_name}', bukan '{tool_args['business_name']}'"}
            token = get_fonnte_token(db)
            if not token:
                return {"success": False, "error": "Fonnte token belum dikonfigurasi. Tambahkan token di Settings."}
            # Get template from database if template_id provided, else use message
            message_text = tool_args.get("message", "")
            template_id = tool_args.get("template_id")
            if template_id:
                tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == template_id, DynamicTemplate.type == "WA_BLAST", DynamicTemplate.is_active == True).first()
                if tmpl:
                    # Replace placeholders in template (support both {{var}} and {var} formats)
                    message_text = tmpl.content
                    message_text = message_text.replace("{{business_name}}", lead.business_name or "").replace("{business_name}", lead.business_name or "")
                    message_text = message_text.replace("{{phone}}", lead.phone_number or "").replace("{phone}", lead.phone_number or "")
                    # Also support custom replacements from args
                    if tool_args.get("replacements"):
                        for key, val in tool_args["replacements"].items():
                            message_text = message_text.replace("{{" + key + "}}", str(val)).replace("{" + key + "}", str(val))
                            message_text = message_text.replace(f"{{{key}}}", str(val))
            import httpx as _httpx
            success = _send_fonnte_sync(lead.phone_number, message_text, token, _httpx)
            if success:
                if lead.status == "Scraped":
                    lead.status = "Contacted"
                    db.commit()
                log_audit(db, current_user.name, "SEND_WA", "leads", lead.id, {"type": "agent", "template_id": template_id})
                return {"success": True, "result": {"lead_id": lead.id, "business_name": lead.business_name, "phone": lead.phone_number, "template_used": bool(template_id)}}
            return {"success": False, "error": "Gagal kirim WA via Fonnte"}

        elif tool_name == "get_lead_details":
            lead = db.query(Lead).filter(Lead.id == tool_args["lead_id"]).first()
            if not lead:
                return {"success": False, "error": f"Lead ID {tool_args.get('lead_id')} tidak ditemukan"}
            # Get projects for this lead
            projects = db.query(Project).filter(Project.lead_id == lead.id).all()
            return {
                "success": True,
                "result": {
                    "id": lead.id,
                    "business_name": lead.business_name,
                    "phone_number": lead.phone_number,
                    "address": lead.address,
                    "status": lead.status,
                    "product_interest": lead.product_interest,
                    "lead_score": lead.lead_score,
                    "google_rating": lead.google_rating,
                    "review_count": lead.review_count,
                    "website_url": lead.website_url,
                    "projects": [{
                        "id": p.id,
                        "name": p.name,
                        "type": p.type,
                        "status": p.status,
                        "nominal": p.nominal,
                        "start_date": p.start_date,
                        "end_date": p.end_date,
                    } for p in projects]
                }
            }

        elif tool_name == "get_client_projects":
            projects = db.query(Project).filter(Project.lead_id == tool_args["lead_id"]).all()
            if not projects:
                return {"success": True, "result": [], "count": 0}
            lead = db.query(Lead).filter(Lead.id == tool_args["lead_id"]).first()
            return {
                "success": True,
                "result": [{
                    "id": p.id,
                    "lead_id": p.lead_id,
                    "business_name": lead.business_name if lead else None,
                    "name": p.name,
                    "type": p.type,
                    "status": p.status,
                    "nominal": p.nominal,
                    "start_date": p.start_date,
                    "end_date": p.end_date,
                } for p in projects],
                "count": len(projects)
            }

        elif tool_name == "update_project":
            project = db.query(Project).filter(Project.id == tool_args["project_id"]).first()
            if not project:
                return {"success": False, "error": f"Project ID {tool_args.get('project_id')} tidak ditemukan"}
            lead = db.query(Lead).filter(Lead.id == project.lead_id).first()
            # Validate business_name if provided
            if tool_args.get("business_name") and lead:
                if tool_args["business_name"].lower() not in lead.business_name.lower():
                    return {"success": False, "error": f"Konfirmasi gagal: project ini milik '{lead.business_name}', bukan '{tool_args['business_name']}'"}
            old_values = {"nominal": project.nominal, "status": project.status}
            if tool_args.get("nominal"):
                project.nominal = tool_args["nominal"]
            if tool_args.get("status"):
                project.status = tool_args["status"]
            db.commit()
            log_audit(db, current_user.name, "UPDATE", "projects", project.id, {"old": old_values, "new": {"nominal": project.nominal, "status": project.status}})
            return {
                "success": True,
                "result": {
                    "project_id": project.id,
                    "business_name": lead.business_name if lead else None,
                    "name": project.name,
                    "nominal": project.nominal,
                    "status": project.status,
                }
            }

        elif tool_name == "get_products":
            products = db.query(Product).filter(Product.is_active == True).all()
            return {
                "success": True,
                "result": [{
                    "id": p.id,
                    "name": p.name,
                    "base_price": p.base_price,
                    "is_retainer": p.is_retainer,
                    "category": p.category,
                } for p in products]
            }

        elif tool_name == "get_wa_templates":
            templates = db.query(DynamicTemplate).filter(
                DynamicTemplate.type == "WA_BLAST",
                DynamicTemplate.is_active == True
            ).all()
            return {
                "success": True,
                "result": [{
                    "id": t.id,
                    "name": t.name,
                    "content": t.content[:500] + "..." if len(t.content) > 500 else t.content,
                } for t in templates],
                "count": len(templates)
            }

        elif tool_name == "get_business_summary":
            total_leads = db.query(Lead).filter(Lead.is_archived == False).count()
            by_status = db.query(Lead.status, func.count(Lead.id)).filter(Lead.is_archived == False).group_by(Lead.status).all()
            total_revenue = db.query(func.sum(Transaction.amount)).filter(Transaction.type == "income").scalar() or 0
            total_expense = db.query(func.sum(Transaction.amount)).filter(Transaction.type == "expense").scalar() or 0
            active_projects = db.query(Project).filter(Project.status == "ACTIVE").count()
            return {
                "success": True,
                "result": {
                    "total_leads": total_leads,
                    "by_status": dict(by_status),
                    "revenue": total_revenue,
                    "expense": total_expense,
                    "profit": total_revenue - total_expense,
                    "active_projects": active_projects,
                }
            }

        elif tool_name == "create_proposal":
            lead = db.query(Lead).filter(Lead.id == tool_args["lead_id"]).first()
            if not lead:
                return {"success": False, "error": f"Lead ID {tool_args.get('lead_id')} tidak ditemukan"}
            # Validate business_name if provided
            if tool_args.get("business_name") and tool_args["business_name"].lower() not in lead.business_name.lower():
                return {"success": False, "error": f"Konfirmasi gagal: lead ID {lead.id} adalah '{lead.business_name}', bukan '{tool_args['business_name']}'"}
            services = json.loads(tool_args["services"]) if isinstance(tool_args["services"], str) else tool_args["services"]
            slug = generate_unique_slug(db, lead.business_name)
            proposal = Proposal(
                lead_id=lead.id,
                services_detail=json.dumps(services),
                total_price=sum(s.get("price", 0) for s in services),
                base_price=sum(s.get("price", 0) for s in services),
                status="Sent",
                created_at=datetime.now(timezone.utc).isoformat(),
                slug=slug,
            )
            db.add(proposal)
            db.commit()
            log_audit(db, current_user.name, "CREATE", "proposals", proposal.id, {"lead_id": lead.id})
            return {
                "success": True,
                "result": {
                    "proposal_id": proposal.id,
                    "slug": slug,
                    "url": f"https://api.kantorteman.my.id/r/{slug}",
                    "lead_id": lead.id,
                    "business_name": lead.business_name,
                    "services": services,
                }
            }

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# AI Chat Endpoints (Semuts.sh Integration)
# ---------------------------------------------------------------------------

@app.get("/api/chat/projects", response_model=List[ChatProjectOut])
def list_chat_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(ChatProject).filter(ChatProject.user_id == current_user.id).order_by(ChatProject.updated_at.desc()).all()
    return projects


@app.post("/api/chat/projects", response_model=ChatProjectOut)
def create_chat_project(body: ChatProjectCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = ChatProject(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        system_prompt=body.system_prompt,
        default_model=body.default_model or "glm-5",
        context_window_size=body.context_window_size or 20,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/api/chat/projects/{project_id}", response_model=ChatProjectOut)
def get_chat_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(ChatProject).filter(ChatProject.id == project_id, ChatProject.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    return project


@app.put("/api/chat/projects/{project_id}", response_model=ChatProjectOut)
def update_chat_project(project_id: str, body: ChatProjectUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(ChatProject).filter(ChatProject.id == project_id, ChatProject.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.system_prompt is not None:
        project.system_prompt = body.system_prompt
    if body.default_model is not None:
        project.default_model = body.default_model
    if body.context_window_size is not None:
        project.context_window_size = body.context_window_size
    project.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(project)
    return project


@app.delete("/api/chat/projects/{project_id}")
def delete_chat_project(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(ChatProject).filter(ChatProject.id == project_id, ChatProject.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")

    # Delete all messages in all conversations
    conversations = db.query(ChatConversation).filter(ChatConversation.project_id == project_id).all()
    for conv in conversations:
        db.query(ChatMessage).filter(ChatMessage.conversation_id == conv.id).delete()

    # Delete all conversations
    db.query(ChatConversation).filter(ChatConversation.project_id == project_id).delete()

    # Delete all memories
    db.query(ChatMemory).filter(ChatMemory.project_id == project_id).delete()

    # Delete project
    db.delete(project)
    db.commit()
    return {"success": True, "message": "Project dihapus"}


@app.get("/api/chat/projects/{project_id}/conversations", response_model=List[ChatConversationOut])
def list_conversations(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(ChatProject).filter(ChatProject.id == project_id, ChatProject.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    conversations = db.query(ChatConversation).filter(ChatConversation.project_id == project_id).order_by(ChatConversation.updated_at.desc()).all()
    return conversations


@app.post("/api/chat/projects/{project_id}/conversations", response_model=ChatConversationOut)
def create_conversation(project_id: str, body: ChatConversationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(ChatProject).filter(ChatProject.id == project_id, ChatProject.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    conversation = ChatConversation(
        project_id=project_id,
        user_id=current_user.id,
        title=body.title or "New Chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@app.get("/api/chat/conversations/{conversation_id}", response_model=ChatConversationOut)
def get_conversation(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id, ChatConversation.user_id == current_user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation tidak ditemukan")
    return conversation


@app.delete("/api/chat/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id, ChatConversation.user_id == current_user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation tidak ditemukan")
    db.delete(conversation)
    db.commit()
    return {"success": True, "message": "Conversation dihapus"}


@app.get("/api/chat/conversations/{conversation_id}/messages", response_model=List[ChatMessageOut])
def list_messages(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id, ChatConversation.user_id == current_user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation tidak ditemukan")
    messages = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at.asc()).all()
    return messages


# RAG Tools - Functions for AI to query business data
def get_business_context(query: str, db: Session) -> str:
    """
    Fleksibel RAG - Automatically query all database tables based on keywords.
    No hardcoding needed - will adapt to any table structure.
    """
    from sqlalchemy import inspect, text as sql_text

    context_parts = []
    query_lower = query.lower()

    # Get all model classes from Base
    model_map = {
        "leads": Lead,
        "contacts": Contact,
        "products": Product,
        "categories": Category,
        "proposals": Proposal,
        "wallets": Wallet,
        "transactions": Transaction,
        "subscriptions": Subscription,
        "ads_campaigns": AdsCampaign,
        "blast_campaigns": BlastCampaign,
        "projects": Project,
        "client_notes": ClientNote,
        "follow_up_sequences": FollowUpSequence,
        "content_schedules": ContentSchedule,
        "scrape_histories": ScrapeHistory,
        "lead_activity_logs": LeadActivityLog,
        "reengagement_alerts": ReengagementAlert,
        "message_templates": MessageTemplate,
        "dynamic_templates": DynamicTemplate,
        "service_items": ServiceItem,
        "provider_configs": ProviderConfig,
    }

    # Keywords mapping to tables
    keyword_table_map = {
        # Leads & Customers
        "lead": ["leads"], "leads": ["leads"], "prospek": ["leads"], "calon": ["leads"],
        # Finance
        "uang": ["transactions", "wallets"], "duit": ["transactions", "wallets"],
        "keuangan": ["transactions", "wallets"], "finance": ["transactions", "wallets"],
        "pendapatan": ["transactions"], "revenue": ["transactions"], "omzet": ["transactions"],
        "pengeluaran": ["transactions"], "expense": ["transactions"],
        "saldo": ["wallets"], "wallet": ["wallets"], "dompet": ["wallets"],
        # Contacts & Clients
        "kontak": ["contacts"], "contact": ["contacts"], "klien": ["contacts", "projects", "client_notes"],
        "client": ["contacts", "projects", "client_notes"], "nasabah": ["contacts"],
        # Products & Services
        "produk": ["products", "categories"], "product": ["products", "categories"],
        "layanan": ["products", "categories"], "service": ["products", "categories"],
        "kategori": ["categories"], "category": ["categories"],
        # Proposals
        "proposal": ["proposals"], "penawaran": ["proposals"], "quote": ["proposals"],
        # Marketing & Ads
        "ads": ["ads_campaigns"], "iklan": ["ads_campaigns"], "campaign": ["ads_campaigns"],
        "advertising": ["ads_campaigns"], "promosi": ["ads_campaigns", "blast_campaigns"],
        "blast": ["blast_campaigns"], "whatsapp blast": ["blast_campaigns"],
        # Subscriptions
        "langganan": ["subscriptions"], "subscription": ["subscriptions"],
        "retainer": ["subscriptions"],
        # Projects
        "project": ["projects"], "proyek": ["projects"],
        # Schedules & Follow-ups
        "jadwal": ["content_schedules", "follow_up_sequences"],
        "schedule": ["content_schedules"], "follow up": ["follow_up_sequences"],
        "konten": ["content_schedules"], "content": ["content_schedules"],
        # Scraping
        "scrape": ["scrape_histories"], "scraping": ["scrape_histories"],
        # Alerts
        "alert": ["reengagement_alerts"], "reengagement": ["reengagement_alerts"],
        # Templates
        "template": ["message_templates", "dynamic_templates"],
        # General business
        "bisnis": ["leads", "transactions", "ads_campaigns", "subscriptions"],
        "usaha": ["leads", "transactions", "ads_campaigns", "subscriptions"],
        "overview": ["leads", "transactions", "ads_campaigns", "subscriptions", "contacts"],
    }

    # Find which tables to query based on keywords
    tables_to_query = set()
    for keyword, tables in keyword_table_map.items():
        if keyword in query_lower:
            tables_to_query.update(tables)

    # If no specific keywords found, give business overview
    if not tables_to_query:
        tables_to_query = {"leads", "transactions", "contacts", "ads_campaigns"}

    # Query each relevant table
    for table_name in tables_to_query:
        if table_name not in model_map:
            continue

        model = model_map[table_name]

        try:
            # Get table data
            records = db.query(model).limit(50).all()

            if not records:
                continue

            # Get column names
            inspector = inspect(model)
            columns = [c.key for c in inspector.mapper.column_attrs]

            # Build context for this table
            table_context = f"\n[DATA {table_name.upper()}]\n"
            table_context += f"Total: {db.query(model).count()} records\n\n"

            # Format records
            for i, record in enumerate(records[:10]):  # Limit to 10 records
                record_data = []
                for col in columns:
                    val = getattr(record, col, None)
                    if val is not None and col not in ["id", "created_at", "updated_at", "deleted_at"]:
                        # Format value
                        if isinstance(val, float):
                            val = f"Rp {val:,.0f}" if "price" in col or "amount" in col or "budget" in col or "balance" in col else f"{val:,.2f}"
                        elif isinstance(val, str) and len(val) > 100:
                            val = val[:100] + "..."
                        record_data.append(f"{col}: {val}")

                if record_data:
                    table_context += f"  - {', '.join(record_data[:5])}\n"

            context_parts.append(table_context)

        except Exception as e:
            # Skip tables that can't be queried
            continue

    # Add summary statistics for key tables
    if "transactions" in tables_to_query:
        total_income = db.query(func.sum(Transaction.amount)).filter(Transaction.type == "income").scalar() or 0
        total_expense = db.query(func.sum(Transaction.amount)).filter(Transaction.type == "expense").scalar() or 0
        context_parts.append(f"\n[RINGKASAN KEUANGAN]\nPemasukan: Rp {total_income:,.0f}\nPengeluaran: Rp {total_expense:,.0f}\nSaldo: Rp {(total_income or 0) - (total_expense or 0):,.0f}")

    if "ads_campaigns" in tables_to_query:
        active = db.query(AdsCampaign).filter(AdsCampaign.status == "ACTIVE").all()
        if active:
            total_budget = sum(c.budget or 0 for c in active)
            context_parts.append(f"\n[RINGKASAN ADS]\nCampaign Aktif: {len(active)}\nTotal Budget: Rp {total_budget:,.0f}")

    return "\n".join(context_parts) if context_parts else "Tidak ada data relevan ditemukan."


@app.post("/api/chat/conversations/{conversation_id}/chat")
async def chat(conversation_id: str, body: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id, ChatConversation.user_id == current_user.id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation tidak ditemukan")

        project = db.query(ChatProject).filter(ChatProject.id == conversation.project_id).first()

        # Get API config from active proxy
        active_proxy = db.query(AIProxy).filter_by(is_active=True).first()
        if not active_proxy:
            raise HTTPException(status_code=400, detail="Tidak ada AI proxy aktif. Tambahkan proxy di Settings.")

        api_key = active_proxy.api_key
        api_base = active_proxy.base_url.rstrip("/")
        model = body.model or project.default_model or (active_proxy.model or "glm-5")

        # Build HYBRID CONTEXT from multiple layers
        context_window = project.context_window_size if project else 20

        # Layer 1: Get conversation summaries (for long context)
        summaries = db.query(ChatSummary).filter(
            ChatSummary.conversation_id == conversation_id
        ).order_by(ChatSummary.created_at.desc()).limit(3).all()

        # Layer 2: Get recent messages (last N messages)
        total_messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).count()

        # If too many messages, trigger summarization
        summary_created = False
        if total_messages > 0 and total_messages % 10 == 0:
            # Get messages to summarize (older than recent window)
            messages_to_summarize = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation_id
            ).order_by(ChatMessage.created_at.asc()).limit(total_messages - 5).all()

            if len(messages_to_summarize) >= 5:
                try:
                    # Create summary using AI
                    summary_text = "Ringkasan percakapan sebelumnya:\n"
                    for msg in messages_to_summarize[-10:]:  # Last 10 of old messages
                        role = "User" if msg.role == "user" else "AI"
                        summary_text += f"- {role}: {msg.content[:200]}...\n"

                    new_summary = ChatSummary(
                        conversation_id=conversation_id,
                        content=summary_text,
                        message_count=len(messages_to_summarize),
                        tokens_saved=len(messages_to_summarize) * 100  # Estimate
                    )
                    db.add(new_summary)
                    summary_created = True
                except Exception:
                    pass

        # Get recent messages after potential summarization
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).order_by(ChatMessage.created_at.desc()).limit(context_window).all()
        recent_messages.reverse()

        messages = []

        # Layer 1: System prompt
        agent_system_prompt = """Asisten bisnis yang MENGEKSEKUSI aksi via tools. BUKAN asisten yang cuma ngomong.

ATURAN UTAMA:
1. Setiap permintaan user WAJIB panggil tool yang sesuai
2. JANGAN pernah jawab dengan teori/menjelaskan - LANGSUNG EKSEKUSI
3. Setelah eksekusi, berikan hasil singkat

Tools:
- create_lead: buat lead/klien baru
- search_leads: cari klien/leads
- get_lead_details: detail klien + proyeknya
- get_client_projects: list proyek klien
- update_project: update harga/status proyek
- create_proposal: buat proposal baru
- update_lead_status: ubah status lead
- send_whatsapp: kirim WA
- get_products: list produk
- get_wa_templates: list template WA
- get_business_summary: ringkasan bisnis

WORKFLOW KHUSUS:
- Untuk tawarkan produk ke klien baru:
  1. create_lead (buat klien)
  2. get_products (pilih produk cocok)
  3. create_proposal (buat proposal, akan return URL)
  4. get_wa_templates (pilih template yang cocok)
  5. send_whatsapp dengan template_id + replacements (termasuk proposal_link dari step 3)

Contoh benar:
User: "Update proyek SEO jadi 1.5jt"
AI: [panggil get_client_projects] -> [panggil update_project dengan nominal 1500000]
Output: "Proyek SEO PT Wijaya diupdate jadi Rp 1.500.000/bulan"

Contoh SALAH (JANGAN):
User: "Update proyek SEO jadi 1.5jt"
AI: "Baik saya akan update proyeknya. Proyek berhasil diupdate..." (tanpa panggil tool)"""

        # Layer 2: Business Data (RAG) - skip for agent mode to force tool usage
        if not body.agent_mode:
            business_context = get_business_context(body.message, db)
            if business_context:
                messages.append({"role": "system", "content": f"Data Bisnis Saat Ini:\n{business_context}"})

        # Layer 3: Memories (Persistent)
        memories = db.query(ChatMemory).filter(ChatMemory.project_id == conversation.project_id).all()
        if memories:
            memory_text = "\n".join([f"- {m.content}" for m in memories])
            messages.append({"role": "system", "content": f"Memory Bank:\n{memory_text}"})

        # Layer 4: Conversation Summaries (for long context)
        if summaries:
            summary_text = "\n".join([s.content for s in reversed(summaries)])
            messages.append({"role": "system", "content": f"Ringkasan Percakapan Sebelumnya:\n{summary_text}"})

        # Layer 5: Recent messages
        for msg in recent_messages:
            messages.append({"role": msg.role, "content": msg.content})

        # Add user message
        messages.append({"role": "user", "content": body.message})

        # Save user message
        user_msg = ChatMessage(
            conversation_id=conversation_id,
            role="user",
            content=body.message,
        )
        db.add(user_msg)
        db.commit()

        # Agent Mode: Tool execution loop
        tool_calls_executed = []
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Call AI API
            async with httpx.AsyncClient(timeout=60) as client:
                # Token efficiency: set max_tokens based on task type
                max_tokens = 500  # default for simple queries
                if body.agent_mode and iteration == 1:
                    max_tokens = 300  # for tool calling, response can be short
                elif body.agent_mode and iteration > 1:
                    max_tokens = 500  # for final response after tool execution

                request_body = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                # Add tools if agent mode enabled
                if body.agent_mode:
                    request_body["tools"] = AGENT_TOOLS
                    # Force tool usage in agent mode - AI must call a tool
                    request_body["tool_choice"] = "required"

                resp = await client.post(
                    f"{api_base.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
                if resp.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"AI API error: {resp.status_code} - {resp.text[:200]}")

                result = resp.json()
                choice = result["choices"][0]
                message = choice["message"]
                tokens_used = result.get("usage", {}).get("total_tokens", 0)

            # Check if AI wants to call tools
            if message.get("tool_calls"):
                # Add assistant message with tool calls to history
                messages.append(message)

                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]
                    tool_call_id = tool_call["id"]

                    try:
                        tool_args = json.loads(tool_args_str)
                    except:
                        tool_args = {}

                    # Execute the tool
                    tool_result = execute_tool_call(tool_name, tool_args, db, current_user)

                    tool_calls_executed.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": tool_result
                    })

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(tool_result)
                    })

                # Continue loop to get final response
                continue

            # No tool calls - we have final response
            assistant_content = message.get("content", "")

            # Post-process: strip decorative elements for token efficiency
            import re
            # Remove emojis
            assistant_content = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]', '', assistant_content)
            # Remove markdown tables
            assistant_content = re.sub(r'\|.*\|', '', assistant_content)
            assistant_content = re.sub(r'^[-:|]+$', '', assistant_content, flags=re.MULTILINE)
            # Remove headers
            assistant_content = re.sub(r'^#{1,6}\s*', '', assistant_content, flags=re.MULTILINE)
            # Remove horizontal rules
            assistant_content = re.sub(r'^---+$', '', assistant_content, flags=re.MULTILINE)
            # Remove excessive bold
            assistant_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', assistant_content)
            # Clean up extra whitespace
            assistant_content = re.sub(r'\n{3,}', '\n\n', assistant_content)
            assistant_content = assistant_content.strip()
            break
        else:
            # Max iterations reached
            assistant_content = "Maaf, saya tidak dapat menyelesaikan permintaan dalam jumlah langkah yang wakin. Silakan coba permintaan yang lebih spesifik."

        # Save assistant message
        assistant_msg = ChatMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            tokens_used=tokens_used,
            model_used=model,
        )
        db.add(assistant_msg)

        # Auto-memory: Extract important info from conversation
        memory_saved = False
        memory_content_saved = None
        total_messages = db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).count()
        if total_messages > 0 and total_messages % 5 == 0:
            try:
                memory_prompt = messages + [
                    {"role": "system", "content": "Analyze the conversation and extract ONE important fact to remember about the user (preferences, name, context, etc). Reply with ONLY the fact, nothing else. If nothing important, reply with 'SKIP'."},
                ]
                async with httpx.AsyncClient(timeout=30) as mem_client:
                    mem_resp = await mem_client.post(
                        f"{api_base.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={"model": model, "messages": memory_prompt, "max_tokens": 200, "stream": False},
                    )
                    if mem_resp.status_code == 200:
                        memory_content = mem_resp.json()["choices"][0]["message"]["content"].strip()
                        if memory_content and memory_content.upper() != "SKIP" and len(memory_content) > 5:
                            # Save to memory bank
                            new_memory = ChatMemory(
                                project_id=conversation.project_id,
                                content=memory_content,
                                pinned_by=current_user.id,
                            )
                            db.add(new_memory)
                            memory_saved = True
                            memory_content_saved = memory_content
            except Exception:
                pass  # Don't fail chat if memory extraction fails

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc).isoformat()
        if project:
            project.updated_at = datetime.now(timezone.utc).isoformat()

        db.commit()

        return {
            "user_message": {
                "id": user_msg.id,
                "role": "user",
                "content": body.message,
                "tokens_used": 0,
                "created_at": user_msg.created_at,
            },
            "message": {
                "id": assistant_msg.id,
                "role": "assistant",
                "content": assistant_content,
                "tokens_used": tokens_used,
                "model_used": model,
                "created_at": assistant_msg.created_at,
            },
            "tool_calls": tool_calls_executed if tool_calls_executed else None,
            "memory_saved": memory_saved,
            "memory_content": memory_content_saved,
            "summary_created": summary_created,
            "context_info": {
                "total_messages": total_messages,
                "recent_messages": len(recent_messages),
                "summaries": len(summaries),
                "memories": len(memories) if memories else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@app.get("/api/chat/projects/{project_id}/memories", response_model=List[ChatMemoryOut])
def list_memories(project_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(ChatProject).filter(ChatProject.id == project_id, ChatProject.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    memories = db.query(ChatMemory).filter(ChatMemory.project_id == project_id).order_by(ChatMemory.created_at.desc()).all()
    return memories


@app.post("/api/chat/projects/{project_id}/memories", response_model=ChatMemoryOut)
def create_memory(project_id: str, body: ChatMemoryCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(ChatProject).filter(ChatProject.id == project_id, ChatProject.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    memory = ChatMemory(
        project_id=project_id,
        content=body.content,
        pinned_by=current_user.id,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


@app.delete("/api/chat/memories/{memory_id}")
def delete_memory(memory_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memory = db.query(ChatMemory).filter(ChatMemory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory tidak ditemukan")
    # Check ownership via project
    project = db.query(ChatProject).filter(ChatProject.id == memory.project_id, ChatProject.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=403, detail="Tidak ada akses ke memory ini")
    db.delete(memory)
    db.commit()
    return {"success": True, "message": "Memory dihapus"}


@app.get("/api/chat/models")
def list_chat_models(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Available models from AIMurah/Semuts
    return {
        "models": [
            {"id": "glm-5", "name": "GLM-5", "description": "Model cepat dan efisien untuk chat umum"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "Model ringan OpenAI"},
            {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "description": "Model cepat dari Anthropic"},
        ]
    }


def reset_fonnte_monthly_quota():
    db = SessionLocal()
    try:
        provider = db.query(ProviderConfig).filter_by(id="FONNTE").first()
        if provider and provider.monthly_quota:
            provider.remaining_quota = provider.monthly_quota
            db.commit()
            print(f"[SCHEDULER] Fonnte quota reset → {provider.monthly_quota}", flush=True)
    except Exception as e:
        print(f"[SCHEDULER ERROR] Fonnte reset: {e}", flush=True)
    finally:
        db.close()


scheduler = AsyncIOScheduler()
scheduler.add_job(process_pending_blasts, "interval", minutes=1, id="blast_processor")
scheduler.add_job(scheduled_followup_processor, "interval", minutes=30, id="followup_processor")
scheduler.add_job(
    process_outreach_lifecycle_states,
    "interval",
    hours=1,
    id="outreach_lifecycle_machine",
    args=[SessionLocal, Lead, Proposal, log_audit],
)
scheduler.add_job(reset_fonnte_monthly_quota, "cron", day=1, hour=0, minute=0, id="fonnte_monthly_reset")


@app.on_event("startup")
def start_scheduler():
    scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()

@app.patch("/api/chat/conversations/{conversation_id}", response_model=ChatConversationOut)
def update_conversation(conversation_id: str, body: ChatConversationUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id, ChatConversation.user_id == current_user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation tidak ditemukan")
    if body.title:
        conversation.title = body.title
        conversation.updated_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        db.refresh(conversation)
    return conversation


# ===========================================================================
# Content Generator
# ===========================================================================

def _get_system_ai_config(db: Session) -> dict:
    key = db.query(SystemSettings).filter_by(key="openai_api_key").first()
    base = db.query(SystemSettings).filter_by(key="ai_base_url").first()
    model_s = db.query(SystemSettings).filter_by(key="ai_model").first()
    api_key = key.value if key and key.value else ""
    if not api_key:
        raise HTTPException(status_code=400, detail="Content Generator AI belum dikonfigurasi. Set API Key di Settings → Content Generator AI.")
    return {
        "api_key": api_key,
        "base_url": (base.value if base and base.value else "https://api.aimurah.com/v1").rstrip("/"),
        "model": model_s.value if model_s and model_s.value else "claude-sonnet-4-5",
    }


def _call_text_gen(messages: list, api_key: str, base_url: str, model: str, max_tokens: int = 2000) -> str:
    import httpx as _httpx
    with _httpx.Client(timeout=120) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"AI API error {resp.status_code}: {resp.text[:200]}")
    try:
        data = resp.json()
    except json.JSONDecodeError:
        # Some proxies return NDJSON even with stream=False — take first valid line
        for line in resp.text.splitlines():
            line = line.strip()
            if line and not line.startswith("data: [DONE]"):
                raw = line.removeprefix("data: ")
                try:
                    data = json.loads(raw)
                    break
                except json.JSONDecodeError:
                    continue
        else:
            raise HTTPException(status_code=502, detail="AI API returned unparseable response")
    return data["choices"][0]["message"]["content"]


def _get_session_ctx(session_id: str, db: Session, limit: int = 5) -> str:
    if not session_id:
        return ""
    gens = (db.query(ContentGeneration)
            .filter(ContentGeneration.session_id == session_id, ContentGeneration.status == "done")
            .order_by(ContentGeneration.created_at.desc()).limit(limit).all())
    if not gens:
        return ""
    parts = []
    for g in reversed(gens):
        try:
            out = json.loads(g.output_data) if g.output_data else {}
        except Exception:
            out = {}
        if g.tool_type == "image":
            images = out.get("images", [])
            preview = f"{len(images)} gambar dihasilkan" if images else "—"
        elif g.tool_type == "caption":
            preview = out.get("caption", "")[:200]
        elif g.tool_type == "seo_article":
            preview = f"[{out.get('title', '')}] {out.get('meta_description', '')[:150]}"
        else:
            preview = str(out)[:200]
        parts.append(f"[{g.tool_type}] {preview}")
    return "Konteks dari sesi ini:\n" + "\n\n".join(parts)


def _get_manual_ctx(context_from: list, db: Session) -> str:
    if not context_from:
        return ""
    gens = db.query(ContentGeneration).filter(ContentGeneration.id.in_(context_from)).all()
    if not gens:
        return ""
    parts = []
    for g in gens:
        try:
            out = json.loads(g.output_data) if g.output_data else {}
        except Exception:
            out = {}
        parts.append(f"[{g.tool_type}] {str(out)[:400]}")
    return "Konteks yang dipilih:\n" + "\n\n".join(parts)


# --- AI Proxy CRUD ---

@app.get("/api/ai-proxies", response_model=List[AIProxyOut])
def list_ai_proxies(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(AIProxy).order_by(AIProxy.created_at.asc()).all()

@app.post("/api/ai-proxies", response_model=AIProxyOut, status_code=201)
def create_ai_proxy(body: AIProxyIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proxy = AIProxy(name=body.name, base_url=body.base_url.rstrip("/"), api_key=body.api_key, model=body.model)
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy

@app.put("/api/ai-proxies/{proxy_id}", response_model=AIProxyOut)
def update_ai_proxy(proxy_id: str, body: AIProxyIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy tidak ditemukan")
    proxy.name = body.name
    proxy.base_url = body.base_url.rstrip("/")
    proxy.api_key = body.api_key
    proxy.model = body.model
    db.commit()
    db.refresh(proxy)
    return proxy

@app.post("/api/ai-proxies/{proxy_id}/activate", response_model=AIProxyOut)
def activate_ai_proxy(proxy_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy tidak ditemukan")
    db.query(AIProxy).update({"is_active": False})
    proxy.is_active = True
    db.commit()
    db.refresh(proxy)
    return proxy

@app.delete("/api/ai-proxies/{proxy_id}", status_code=204)
def delete_ai_proxy(proxy_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proxy = db.query(AIProxy).filter_by(id=proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy tidak ditemukan")
    db.delete(proxy)
    db.commit()


# --- Content Provider CRUD ---

@app.get("/api/content/providers", response_model=List[ContentProviderOut])
def list_content_providers(
    tool_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ContentProvider)
    if tool_type:
        q = q.filter(ContentProvider.tool_type == tool_type)
    providers = q.order_by(ContentProvider.created_at.desc()).all()
    result = []
    for p in providers:
        out = ContentProviderOut.model_validate(p)
        if out.api_key:
            out.api_key = out.api_key[:6] + "***"
        if p.extra_params:
            try:
                out.extra_params = json.loads(p.extra_params)
            except Exception:
                pass
        result.append(out)
    return result


@app.post("/api/content/providers", response_model=ContentProviderOut, status_code=201)
def create_content_provider(
    body: ContentProviderIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = ContentProvider(
        id=str(uuid.uuid4()), name=body.name, tool_type=body.tool_type,
        base_url=body.base_url.rstrip("/"), api_key=body.api_key, model=body.model,
        extra_params=json.dumps(body.extra_params) if body.extra_params else None,
        is_active=body.is_active,
    )
    db.add(p); db.commit(); db.refresh(p)
    out = ContentProviderOut.model_validate(p)
    if out.api_key:
        out.api_key = out.api_key[:6] + "***"
    return out


@app.put("/api/content/providers/{provider_id}", response_model=ContentProviderOut)
def update_content_provider(
    provider_id: str, body: ContentProviderIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(ContentProvider).filter(ContentProvider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    p.name = body.name; p.tool_type = body.tool_type
    p.base_url = body.base_url.rstrip("/"); p.model = body.model; p.is_active = body.is_active
    p.extra_params = json.dumps(body.extra_params) if body.extra_params else None
    if body.api_key and not body.api_key.endswith("***"):
        p.api_key = body.api_key
    db.commit(); db.refresh(p)
    out = ContentProviderOut.model_validate(p)
    if out.api_key:
        out.api_key = out.api_key[:6] + "***"
    return out


@app.delete("/api/content/providers/{provider_id}", status_code=204)
def delete_content_provider(
    provider_id: str, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(ContentProvider).filter(ContentProvider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Provider tidak ditemukan")
    db.delete(p); db.commit()


# --- Content Session CRUD ---

@app.get("/api/content/sessions", response_model=List[ContentSessionOut])
def list_content_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (db.query(ContentSession)
            .filter(ContentSession.user_id == current_user.id)
            .order_by(ContentSession.created_at.desc()).all())


@app.post("/api/content/sessions", response_model=ContentSessionOut, status_code=201)
def create_content_session(
    body: ContentSessionIn, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = ContentSession(id=str(uuid.uuid4()), user_id=current_user.id,
                       name=body.name, description=body.description)
    db.add(s); db.commit(); db.refresh(s)
    return s


@app.delete("/api/content/sessions/{session_id}", status_code=204)
def delete_content_session(
    session_id: str, current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(ContentSession).filter(
        ContentSession.id == session_id, ContentSession.user_id == current_user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    db.query(ContentGeneration).filter(ContentGeneration.session_id == session_id).delete()
    db.delete(s); db.commit()


@app.put("/api/content/sessions/{session_id}", response_model=ContentSessionOut)
def update_content_session(
    session_id: str, body: ContentSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(ContentSession).filter(
        ContentSession.id == session_id, ContentSession.user_id == current_user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")
    s.name = body.name
    if body.description is not None:
        s.description = body.description
    db.commit(); db.refresh(s)
    return s


# --- History ---

@app.get("/api/content/generations")
def list_content_generations(
    session_id: Optional[str] = Query(None),
    tool_type: Optional[str] = Query(None),
    limit: int = Query(20),
    q: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ContentGeneration).filter(ContentGeneration.user_id == current_user.id)
    if session_id:
        query = query.filter(ContentGeneration.session_id == session_id)
    if tool_type:
        query = query.filter(ContentGeneration.tool_type == tool_type)
    if q:
        search = f"%{q}%"
        query = query.filter(
            ContentGeneration.input_data.ilike(search) | ContentGeneration.output_data.ilike(search)
        )
    gens = query.order_by(ContentGeneration.created_at.desc()).limit(limit).all()
    result = []
    for g in gens:
        item = {
            "id": g.id, "session_id": g.session_id, "tool_type": g.tool_type,
            "model_used": g.model_used, "provider_name": g.provider_name,
            "status": g.status, "error_msg": g.error_msg, "created_at": g.created_at,
        }
        try:
            item["input_data"] = json.loads(g.input_data)
        except Exception:
            item["input_data"] = {}
        try:
            item["output_data"] = json.loads(g.output_data) if g.output_data else None
        except Exception:
            item["output_data"] = g.output_data
        result.append(item)
    return result


@app.delete("/api/content/generations/{generation_id}", status_code=204)
def delete_content_generation(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gen = db.query(ContentGeneration).filter(
        ContentGeneration.id == generation_id,
        ContentGeneration.user_id == current_user.id,
    ).first()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    db.delete(gen)
    db.commit()
    return


# --- Generate: Image ---

@app.post("/api/content/generate/image")
def generate_image(
    body: ImageGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = db.query(ContentProvider).filter(
        ContentProvider.id == body.provider_id,
        ContentProvider.tool_type == "image",
        ContentProvider.is_active == True,
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Image provider tidak ditemukan atau tidak aktif")

    gen = ContentGeneration(
        id=str(uuid.uuid4()), user_id=current_user.id, session_id=body.session_id,
        tool_type="image",
        input_data=json.dumps({"prompt": body.prompt, "negative_prompt": body.negative_prompt,
                               "width": body.width, "height": body.height, "provider": provider.name}),
        model_used=provider.model, provider_name=provider.name, status="pending",
    )
    db.add(gen); db.commit()

    try:
        extra = json.loads(provider.extra_params) if provider.extra_params else {}
        payload = {"model": provider.model, "prompt": body.prompt, "n": 1,
                   "size": f"{body.width}x{body.height}", **extra}
        if body.negative_prompt:
            payload["negative_prompt"] = body.negative_prompt

        import httpx as _httpx
        with _httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{provider.base_url}/images/generations",
                headers={"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code != 200:
            raise Exception(f"Image API error {resp.status_code}: {resp.text[:300]}")

        items = resp.json().get("data", [])
        images = []
        for item in items:
            if "url" in item:
                images.append({"type": "url", "value": item["url"]})
            elif "b64_json" in item:
                images.append({"type": "b64", "value": item["b64_json"]})

        gen.output_data = json.dumps({"images": images})
        gen.status = "done"; db.commit()
        return {"id": gen.id, "status": "done", "images": images, "created_at": gen.created_at}

    except HTTPException:
        raise
    except Exception as e:
        gen.status = "error"; gen.error_msg = str(e); db.commit()
        raise HTTPException(status_code=502, detail=f"Gagal generate image: {str(e)}")


# --- Generate: Caption ---

@app.post("/api/content/generate/caption")
def generate_caption(
    body: CaptionGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ai = _get_system_ai_config(db)
    if not ai["api_key"]:
        raise HTTPException(status_code=400, detail="API Key AI belum dikonfigurasi di Settings")

    platform_guide = {
        "instagram": "Instagram: max 2200 karakter, 3-5 hashtag relevan, emoji secukupnya, CTA di akhir.",
        "tiktok": "TikTok: singkat dan catchy, hook kuat di kalimat pertama, 5-10 hashtag trending.",
    }.get(body.platform, "")

    system_msg = (
        f"Kamu adalah content writer media sosial profesional Bahasa Indonesia. "
        f"Buat caption {body.platform.upper()} yang engaging, tone: '{body.tone}'. {platform_guide} "
        f"WAJIB return valid JSON: {{\"caption\": \"...\", \"hashtags\": [\"#tag\"], \"notes\": \"tip singkat\"}}"
    )
    user_msg = f"Topik: {body.topic}"
    if body.keywords:
        user_msg += f"\nKeyword wajib disebut: {', '.join(body.keywords)}"
    ctx = _get_session_ctx(body.session_id, db)
    if ctx:
        user_msg += f"\n\n{ctx}"
    mctx = _get_manual_ctx(body.context_from or [], db)
    if mctx:
        user_msg += f"\n\n{mctx}"

    gen = ContentGeneration(
        id=str(uuid.uuid4()), user_id=current_user.id, session_id=body.session_id,
        tool_type="caption", input_data=json.dumps(body.model_dump()),
        model_used=ai["model"], provider_name="System AI", status="pending",
    )
    db.add(gen); db.commit()

    try:
        text = _call_text_gen(
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            api_key=ai["api_key"], base_url=ai["base_url"], model=ai["model"], max_tokens=800,
        )
        import re as _re
        m = _re.search(r'\{[\s\S]*\}', text)
        try:
            result = json.loads(m.group()) if m else {"caption": text, "hashtags": [], "notes": ""}
        except Exception:
            result = {"caption": text, "hashtags": [], "notes": ""}

        gen.output_data = json.dumps(result); gen.status = "done"; db.commit()
        return {"id": gen.id, "status": "done", "created_at": gen.created_at, **result}

    except HTTPException:
        raise
    except Exception as e:
        gen.status = "error"; gen.error_msg = str(e); db.commit()
        raise HTTPException(status_code=502, detail=f"Gagal generate caption: {str(e)}")


# --- Generate: SEO Article ---

@app.post("/api/content/generate/seo-article")
def generate_seo_article(
    body: SeoArticleGenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ai = _get_system_ai_config(db)
    if not ai["api_key"]:
        raise HTTPException(status_code=400, detail="API Key AI belum dikonfigurasi di Settings")

    target_title = body.title or f"Panduan Lengkap: {body.keyword}"

    intent_guide = {
        "informational": "Search intent INFORMATIONAL: edukasi pembaca, jawab 'apa', 'bagaimana', 'mengapa'. Buat artikel komprehensif dengan definisi jelas, contoh praktis, dan takeaway.",
        "commercial": "Search intent COMMERCIAL INVESTIGATION: pembaca sedang membandingkan pilihan. Sertakan perbandingan, pro-kontra, kriteria pemilihan, dan rekomendasi konkret.",
        "transactional": "Search intent TRANSACTIONAL: pembaca siap bertindak. CTA kuat, benefit produk/jasa menonjol, hilangkan keraguan, sertakan social proof.",
        "navigational": "Search intent NAVIGATIONAL: bantu user menemukan brand/resource spesifik. Fokus pada brand credibility dan unique value proposition.",
    }.get(body.search_intent or "informational", "")

    kd_guide = ""
    if body.keyword_difficulty is not None:
        if body.keyword_difficulty >= 70:
            kd_guide = f"Keyword difficulty {body.keyword_difficulty}/100 (HARD): artikel harus sangat komprehensif, lebih mendalam dari kompetitor, sertakan data/statistik, expert insight."
        elif body.keyword_difficulty >= 40:
            kd_guide = f"Keyword difficulty {body.keyword_difficulty}/100 (MEDIUM): artikel solid dan lengkap, pastikan semua subtopik penting tercakup."
        else:
            kd_guide = f"Keyword difficulty {body.keyword_difficulty}/100 (EASY): fokus pada kualitas dan kegunaan, pastikan E-E-A-T terpenuhi."

    serp_guide = ""
    if body.serp_features:
        hints = []
        if "featured_snippet" in body.serp_features:
            hints.append("tambah definition box atau tabel ringkasan di awal untuk optimasi Featured Snippet")
        if "paa" in body.serp_features:
            hints.append("sertakan FAQ section (H2 'Pertanyaan Umum') untuk optimasi People Also Ask")
        if "local_pack" in body.serp_features:
            hints.append("sertakan informasi lokal yang relevan untuk optimasi Local Pack")
        if "image_pack" in body.serp_features:
            hints.append("tambah deskripsi/caption gambar yang informatif untuk optimasi Image Pack")
        if hints:
            serp_guide = "SERP features target: " + "; ".join(hints) + "."

    system_msg = (
        f"Kamu adalah SEO content writer profesional Bahasa Indonesia, expert dalam E-E-A-T dan on-page SEO. "
        f"Buat artikel blog SEO berkualitas tinggi, tone: '{body.tone}', target sekitar {body.word_count} kata. "
        f"{intent_guide} {kd_guide} {serp_guide} "
        f"Gunakan heading H2/H3 dengan format markdown (## dan ###). "
        f"Optimalkan keyword secara natural (density 1-2%, jangan keyword stuffing). "
        f"Struktur artikel: hook intro, isi dengan heading logis, kesimpulan + CTA. "
        f"WAJIB output dengan format TEPAT berikut (jangan tambah teks lain di luar format):\n"
        f"TITLE: <judul artikel>\n"
        f"META: <meta description max 160 karakter, include keyword>\n"
        f"FOCUS_KEYWORD: <keyword utama>\n"
        f"SECONDARY_KEYWORDS: <keyword1>, <keyword2>, <keyword3>\n"
        f"---ARTICLE---\n"
        f"<artikel lengkap dalam markdown>\n"
        f"---END---"
    )

    user_parts = [f"Keyword utama: {body.keyword}", f"Judul: {target_title}"]
    if body.search_intent:
        user_parts.append(f"Search intent: {body.search_intent}")
    if body.search_volume:
        user_parts.append(f"Search volume: {body.search_volume:,}/bulan")
    if body.keyword_difficulty is not None:
        user_parts.append(f"Keyword difficulty: {body.keyword_difficulty}/100")
    if body.lsi_keywords:
        user_parts.append(f"LSI/related keywords (sisipkan secara natural): {', '.join(body.lsi_keywords)}")
    if body.target_audience:
        user_parts.append(f"Target pembaca: {body.target_audience}")
    if body.target_location:
        user_parts.append(f"Target lokasi: {body.target_location}")
    if body.brand_name:
        user_parts.append(f"Brand/bisnis: {body.brand_name}")
    if body.unique_angle:
        user_parts.append(f"Angle unik artikel ini: {body.unique_angle}")
    if body.faq_topics:
        user_parts.append(f"FAQ topics yang wajib dijawab: {'; '.join(body.faq_topics)}")
    if body.internal_link_targets:
        user_parts.append(f"Halaman internal untuk disarankan sebagai internal link: {body.internal_link_targets}")
    user_msg = "\n".join(user_parts)
    ctx = _get_session_ctx(body.session_id, db)
    if ctx:
        user_msg += f"\n\n{ctx}"
    mctx = _get_manual_ctx(body.context_from or [], db)
    if mctx:
        user_msg += f"\n\n{mctx}"

    gen = ContentGeneration(
        id=str(uuid.uuid4()), user_id=current_user.id, session_id=body.session_id,
        tool_type="seo_article", input_data=json.dumps(body.model_dump()),
        model_used=ai["model"], provider_name="System AI", status="pending",
    )
    db.add(gen); db.commit()

    try:
        text = _call_text_gen(
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            api_key=ai["api_key"], base_url=ai["base_url"], model=ai["model"], max_tokens=4000,
        )
        import re as _re
        def _parse_delimited(t: str) -> dict:
            title = (_re.search(r'^TITLE:\s*(.+)', t, _re.MULTILINE) or _re.search(r'', t))
            meta = _re.search(r'^META:\s*(.+)', t, _re.MULTILINE)
            fk = _re.search(r'^FOCUS_KEYWORD:\s*(.+)', t, _re.MULTILINE)
            sk = _re.search(r'^SECONDARY_KEYWORDS:\s*(.+)', t, _re.MULTILINE)
            body_m = _re.search(r'---ARTICLE---([\s\S]*?)---END---', t)
            return {
                "title": title.group(1).strip() if title and title.lastindex else target_title,
                "meta_description": meta.group(1).strip() if meta else "",
                "focus_keyword": fk.group(1).strip() if fk else body.keyword,
                "secondary_keywords": [k.strip() for k in sk.group(1).split(",") if k.strip()] if sk else [],
                "body": body_m.group(1).strip() if body_m else t,
            }
        result = _parse_delimited(text)

        gen.output_data = json.dumps(result); gen.status = "done"; db.commit()
        return {"id": gen.id, "status": "done", "created_at": gen.created_at, **result}

    except HTTPException:
        raise
    except Exception as e:
        gen.status = "error"; gen.error_msg = str(e); db.commit()
        raise HTTPException(status_code=502, detail=f"Gagal generate artikel: {str(e)}")


# --- CMS Proxy ---

class CmsPublishRequest(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    meta_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    status: str = "draft"

@app.post("/api/cms/publish-article")
def cms_publish_article(body: CmsPublishRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cms_url_row = db.query(SystemSettings).filter_by(key="cms_url").first()
    cms_token_row = db.query(SystemSettings).filter_by(key="cms_api_token").first()
    if not cms_url_row or not cms_url_row.value:
        raise HTTPException(status_code=400, detail="CMS URL belum diset di Settings")
    if not cms_token_row or not cms_token_row.value:
        raise HTTPException(status_code=400, detail="CMS API Token belum diset di Settings")
    import httpx as _httpx
    try:
        resp = _httpx.post(
            f"{cms_url_row.value.rstrip('/')}/api/articles",
            headers={"Authorization": f"Bearer {cms_token_row.value}", "Content-Type": "application/json"},
            json=body.model_dump(),
            timeout=30,
            follow_redirects=True,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"CMS error {resp.status_code}: {resp.text[:300]}")
        return resp.json()
    except _httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Gagal koneksi ke CMS: {str(e)}")


# ---------------------------------------------------------------------------
# Document Archive: Folders & Documents
# ---------------------------------------------------------------------------

class ArchiveFolderIn(BaseModel):
    name: str
    parent_id: Optional[str] = None
    color: Optional[str] = "#6B7280"


class ArchiveFolderUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class ArchiveDocIn(BaseModel):
    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = []
    folder_id: Optional[str] = None


class ArchiveDocUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    folder_id: Optional[str] = None


@app.get("/api/archive/folders")
def list_archive_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folders = db.query(DocumentFolder).filter(DocumentFolder.user_id == current_user.id).order_by(DocumentFolder.created_at).all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "parent_id": f.parent_id,
            "color": f.color,
            "created_at": f.created_at,
        }
        for f in folders
    ]


@app.post("/api/archive/folders", status_code=201)
def create_archive_folder(
    body: ArchiveFolderIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = DocumentFolder(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=body.name.strip(),
        parent_id=body.parent_id or None,
        color=body.color or "#6B7280",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(folder)
    db.commit()
    return {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id, "color": folder.color, "created_at": folder.created_at}


@app.put("/api/archive/folders/{folder_id}")
def update_archive_folder(
    folder_id: str,
    body: ArchiveFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id, DocumentFolder.user_id == current_user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    if body.name is not None:
        folder.name = body.name.strip()
    if body.color is not None:
        folder.color = body.color
    db.commit()
    return {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id, "color": folder.color, "created_at": folder.created_at}


@app.delete("/api/archive/folders/{folder_id}", status_code=204)
def delete_archive_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id, DocumentFolder.user_id == current_user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    db.query(Document).filter(Document.folder_id == folder_id).update({"folder_id": None})
    db.delete(folder)
    db.commit()


@app.get("/api/archive")
def list_archive_docs(
    folder_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    unfoldered: Optional[bool] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Document).filter(Document.user_id == current_user.id)
    if unfoldered:
        q = q.filter(Document.folder_id == None)
    elif folder_id is not None:
        q = q.filter(Document.folder_id == folder_id)
    if search:
        q = q.filter(Document.title.ilike(f"%{search}%"))
    docs = q.order_by(Document.updated_at.desc(), Document.created_at.desc()).limit(limit).all()
    return [_archive_doc_to_dict(d) for d in docs]


@app.post("/api/archive", status_code=201)
def create_archive_doc(
    body: ArchiveDocIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc).isoformat()
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        folder_id=body.folder_id or None,
        title=body.title.strip(),
        body=body.body or None,
        url=body.url or None,
        tags=json.dumps(body.tags or []),
        created_at=now,
        updated_at=now,
    )
    db.add(doc)
    db.commit()
    return _archive_doc_to_dict(doc)


@app.get("/api/archive/{doc_id}")
def get_archive_doc(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    return _archive_doc_to_dict(doc)


@app.put("/api/archive/{doc_id}")
def update_archive_doc(
    doc_id: str,
    body: ArchiveDocUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    if body.title is not None:
        doc.title = body.title.strip()
    if body.body is not None:
        doc.body = body.body
    if body.url is not None:
        doc.url = body.url
    if body.tags is not None:
        doc.tags = json.dumps(body.tags)
    if body.folder_id is not None:
        doc.folder_id = body.folder_id if body.folder_id != "" else None
    doc.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return _archive_doc_to_dict(doc)


@app.delete("/api/archive/{doc_id}", status_code=204)
def delete_archive_doc(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    db.delete(doc)
    db.commit()


def _archive_doc_to_dict(doc: Document) -> dict:
    try:
        tags = json.loads(doc.tags) if doc.tags else []
    except Exception:
        tags = []
    return {
        "id": doc.id,
        "folder_id": doc.folder_id,
        "title": doc.title,
        "body": doc.body,
        "url": doc.url,
        "tags": tags,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }
