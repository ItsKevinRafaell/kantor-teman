# Barrel export - re-export everything from domain sub-modules
from .base import Base, engine, SessionLocal, get_db, log_audit, DATABASE_URL

from .user import User, SystemSettings
from .ai import AIProxy, ProviderConfig, AIModel
from .lead import (
    Lead, Contact, MessageTemplate, ScrapeHistory,
    LeadActivityLog, LeadAnalysis, FollowUpSequence,
    ReengagementAlert, AuditLog
)
from .proposal import Proposal, ServiceItem, ProposalAnalytics
from .product import Category, Product, DynamicTemplate
from .finance import Wallet, Transaction, Subscription, PaymentMethod
from .project import Project, ClientNote, ClientCredential, ClientDocument
from .board import (
    Board, BoardColumn, BoardCard, BoardCardComment,
    BoardCardChecklist, BoardCardActivity
)
from .campaign import AdsCampaign, BlastCampaign, BlastMessage
from .workspace import (
    WorkspaceSheet, WorkspaceColumn, WorkspaceRow,
    WorkspaceCell, WorkspaceAttachment
)
from .content import (
    ContentSchedule, ContentProvider, ContentSession, ContentGeneration
)
from .document import (
    DocumentFolder, Document, BrandKit, BrandAsset,
    DocumentTemplate, GeneratedDocument, DocumentSequence
)

__all__ = [
    # base
    "Base", "engine", "SessionLocal", "get_db", "log_audit", "DATABASE_URL",
    # user
    "User", "SystemSettings",
    # ai
    "AIProxy", "ProviderConfig", "AIModel",
    # lead
    "Lead", "Contact", "MessageTemplate", "ScrapeHistory",
    "LeadActivityLog", "LeadAnalysis", "FollowUpSequence",
    "ReengagementAlert", "AuditLog",
    # proposal
    "Proposal", "ServiceItem", "ProposalAnalytics",
    # product
    "Category", "Product", "DynamicTemplate",
    # finance
    "Wallet", "Transaction", "Subscription", "PaymentMethod",
    # project
    "Project", "ClientNote", "ClientCredential", "ClientDocument",
    # board
    "Board", "BoardColumn", "BoardCard", "BoardCardComment",
    "BoardCardChecklist", "BoardCardActivity",
    # campaign
    "AdsCampaign", "BlastCampaign", "BlastMessage",
    # workspace
    "WorkspaceSheet", "WorkspaceColumn", "WorkspaceRow",
    "WorkspaceCell", "WorkspaceAttachment",
    # content
    "ContentSchedule", "ContentProvider", "ContentSession", "ContentGeneration",
    # document
    "DocumentFolder", "Document", "BrandKit", "BrandAsset",
    "DocumentTemplate", "GeneratedDocument", "DocumentSequence",
]
