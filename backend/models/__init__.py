import os
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, ForeignKey, select, func, DateTime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship, joinedload, selectinload
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leads.db")
# Auto-register PyMySQL for MySQL connections
if "mysql" in DATABASE_URL and "pymysql" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://")
_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

# Use connection pooling for better performance (except SQLite)
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args=_connect_args, poolclass=NullPool)
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args=_connect_args,
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="admin")  # admin / member


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
    feature = Column(String(50), nullable=True, index=True)  # chat|agent|content|analysis|followup, NULL=fallback
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
    last_followup_at = Column(String(255), nullable=True)
    sales_owner = Column(String(255), nullable=True)
    next_action_at = Column(String(255), nullable=True)
    loss_reason = Column(String(500), nullable=True)
    do_not_contact = Column(Boolean, default=False, nullable=False)


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
    status = Column(String(255), default="sent", nullable=False)
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
    accepted_at = Column(String(255), nullable=True)
    rejected_at = Column(String(255), nullable=True)
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
    event = Column(String(50), nullable=True)
    duration_seconds = Column(Integer, nullable=True)


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


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # e.g. "Bank BCA", "GoPay"
    account_number = Column(String(255), nullable=True)  # rekening / nomor
    account_name = Column(String(255), nullable=True)  # atas nama
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    position = Column(Integer, default=0)


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
    batch_name = Column(String(255), nullable=True)


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
    service_type = Column(String(50), nullable=True)
    contract_months = Column(Integer, nullable=True, default=1)
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


class BlastMessage(Base):
    __tablename__ = "blast_messages"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String(36), ForeignKey("blast_campaigns.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey("dynamic_templates.id"), nullable=True, index=True)
    phone_number = Column(String(255), nullable=False, index=True)
    sent_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    delivered_at = Column(String(255), nullable=True)
    read_at = Column(String(255), nullable=True)
    replied_at = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="sent")
    error_message = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Workspace Klien Models
# ---------------------------------------------------------------------------

class WorkspaceSheet(Base):
    __tablename__ = "workspace_sheets"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    sheet_index = Column(Integer, nullable=False)
    sheet_label = Column(String(100), nullable=False)
    service_type = Column(String(50), nullable=True)
    month_number = Column(Integer, nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(255), nullable=True)
    project = relationship("Project", backref="workspace_sheets")


class WorkspaceColumn(Base):
    __tablename__ = "workspace_columns"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sheet_id = Column(String(36), ForeignKey("workspace_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    column_key = Column(String(100), nullable=False)
    column_label = Column(String(100), nullable=False)
    column_type = Column(String(30), nullable=False, default="text")
    column_options = Column(Text, nullable=True)
    column_order = Column(Integer, nullable=False, default=0)
    is_system = Column(Boolean, default=False)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    sheet = relationship("WorkspaceSheet", backref="columns")


class WorkspaceRow(Base):
    __tablename__ = "workspace_rows"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sheet_id = Column(String(36), ForeignKey("workspace_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    row_order = Column(Integer, nullable=False, default=0)
    board_card_id = Column(String(36), ForeignKey("board_cards.id", ondelete="SET NULL"), nullable=True)
    is_template = Column(Boolean, default=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(255), nullable=True)
    sheet = relationship("WorkspaceSheet", backref="rows")


class WorkspaceCell(Base):
    __tablename__ = "workspace_cells"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    row_id = Column(String(36), ForeignKey("workspace_rows.id", ondelete="CASCADE"), nullable=False, index=True)
    column_id = Column(String(36), ForeignKey("workspace_columns.id", ondelete="CASCADE"), nullable=False, index=True)
    value_text = Column(Text, nullable=True)
    value_bool = Column(Boolean, nullable=True)
    value_number = Column(Float, nullable=True)
    value_date = Column(String(50), nullable=True)
    value_json = Column(Text, nullable=True)
    updated_at = Column(String(255), nullable=True)
    row = relationship("WorkspaceRow", backref="cells")
    column = relationship("WorkspaceColumn", backref="cells")


class WorkspaceAttachment(Base):
    __tablename__ = "workspace_attachments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    row_id = Column(String(36), ForeignKey("workspace_rows.id", ondelete="CASCADE"), nullable=False, index=True)
    column_id = Column(String(36), ForeignKey("workspace_columns.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=True)
    uploaded_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    row = relationship("WorkspaceRow", backref="attachments")


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


class AIModel(Base):
    __tablename__ = "ai_models"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)  # display name (e.g. "Claude Haiku 4.5")
    model_id = Column(String(255), nullable=False)  # provider model ID (e.g. "claude-haiku-4-5-20251001")
    description = Column(Text, nullable=True)
    capabilities = Column(Text, nullable=False, default='["chat"]')  # JSON: ["chat", "image", "article", "analysis"]
    is_active = Column(Integer, default=1)
    is_default_chat = Column(Integer, default=0)
    is_default_image = Column(Integer, default=0)
    is_default_article = Column(Integer, default=0)
    is_default_analysis = Column(Integer, default=0)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


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


class BrandKit(Base):
    __tablename__ = "brand_kits"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kit_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class BrandAsset(Base):
    __tablename__ = "brand_assets"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kit_id = Column(String(36), ForeignKey("brand_kits.id"), nullable=False)
    asset_type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    value = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    position = Column(Integer, default=0)
    asset_metadata = Column(Text, nullable=True)
    kit = relationship("BrandKit", backref="assets")


class DocumentTemplate(Base):
    __tablename__ = "document_templates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    html_template = Column(Text, nullable=False)
    variables = Column(Text, nullable=True, default="[]")
    is_active = Column(Boolean, default=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String(36), ForeignKey("document_templates.id"), nullable=True)
    template_name = Column(String(255), nullable=True)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(255), nullable=True)
    variables_used = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    display_filename = Column(String(500), nullable=True)
    generated_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    generated_by = Column(String(255), nullable=True)
    template = relationship("DocumentTemplate", backref="generated_docs")


class DocumentSequence(Base):
    __tablename__ = "document_sequences"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(String(255), nullable=False)
    template_type = Column(String(50), nullable=False)
    last_seq = Column(Integer, nullable=False, default=0)


if os.environ.get("RUN_CREATE_ALL", "").lower() == "true":
    Base.metadata.create_all(bind=engine)

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

