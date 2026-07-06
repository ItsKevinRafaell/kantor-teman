import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any

from .auth import (
    LoginIn, TokenOut, UserUpdate, UserCreate, UserAdminUpdate,
    PasswordResetRequest, PasswordResetConfirm,
)
from .lead import (
    Business, LeadOut, ContactOut, ContactUpdate, TemplateIn, TemplateOut,
    StatusUpdate, LeadSalesUpdate, ProductUpdate, BlastIn, RatingUpdate,
    LeadCreate, LeadEdit, WaSendIn, ExternalLeadIn,
    ScoreAdjustmentUpdate, ScoringSettingsUpdate,
)
from .proposal import (
    ServiceDetail, TimelineItem, ProposalIn, ProposalOut,
    ServiceItemIn, ServiceItemOut, TrackOpenIn, TrackPingIn,
    AnalyticsOut, ProposalAcceptIn, ProposalRejectIn,
)
from .finance import (
    WalletIn, WalletOut, TransactionIn, TransactionOut,
    SubscriptionIn, SubscriptionOut, PaymentMethodIn, PaymentMethodOut,
    FinanceReportOut,
)
from .product import (
    CategoryIn, CategoryOut, ProductIn, ProductOut,
    DynamicTemplateIn, DynamicTemplateOut,
)
from .workspace import (
    WorkspaceInitIn, WorkspaceCellUpdate, WorkspaceRowIn, WorkspaceColumnIn,
    WorkspaceColumnUpdate, WorkspaceSheetUpdate,
)
from .board import (
    LeadMin, BoardCardCommentOut, BoardCardChecklistOut, BoardCardActivityOut, BoardCardAttachmentOut,
    BoardCardOut, BoardColumnOut, BoardOut, BoardColumnIn, BoardCardIn,
    BoardCardUpdate, MoveCardRequest, BoardCardCommentIn, BoardCardChecklistIn,
)
from .project import ProjectIn, ProjectOut, ClientNoteIn, ClientNoteOut, ProjectRiwayatIn, ProjectRiwayatOut
from .credential import (
    CredentialFieldIn, CredentialIn, CredentialFieldOut, CredentialOut,
    CredentialUpdate,
)
from .document import (
    DocumentIn, DocumentOut, BrandKitUpdate, BrandAssetIn,
    DocumentTemplateIn, DocumentGenerateIn, DocumentEmailIn, InvoiceSequenceIn,
    DocumentWorkflowUpdate, DocumentDraftIn, DocumentDraftOut,
    DocumentEditIn, DocumentVersionOut,
)
from .campaign import (
    AdsCampaignIn, AdsCampaignUpdate, AdsCampaignOut,
    BlastCampaignIn, BlastCampaignOut, FonnteWebhookIn,
)
from .content import (
    ContentScheduleIn, ContentScheduleUpdate, ContentScheduleOut,
    ContentProviderIn, ContentProviderOut, ContentSessionIn,
    ContentSessionUpdate, ContentSessionOut, ContentGenerationOut,
    ImageGenRequest, CaptionGenRequest, SeoArticleGenRequest, CmsPublishRequest,
)
from .ai import AIModelIn, AIModelOut, AIProxyIn, AIProxyOut, ProviderConfigOut
from .archive import (
    ArchiveFolderIn, ArchiveFolderUpdate, ArchiveDocIn, ArchiveDocUpdate,
)
from .office import (
    OfficeChatAttachment, OfficeChatRequest, OfficeAgentCreate,
    OfficeSoulUpdate, OfficeEnvUpdate, OfficeConfigUpdate,
)
from .tracking import TrackActivityBody, ViewDurationIn
from .admin import SettingsUpdate, DataAdminBody

__all__ = [
    # base types (for router imports)
    "BaseModel", "Field", "field_validator",
    "Optional", "List", "Any",
    # auth
    "LoginIn", "TokenOut", "UserUpdate", "UserCreate", "UserAdminUpdate",
    "PasswordResetRequest", "PasswordResetConfirm",
    # lead
    "Business", "LeadOut", "ContactOut", "ContactUpdate", "TemplateIn", "TemplateOut",
    "StatusUpdate", "LeadSalesUpdate", "ProductUpdate", "BlastIn", "RatingUpdate",
    "LeadCreate", "LeadEdit", "WaSendIn", "ExternalLeadIn",
    "ScoreAdjustmentUpdate", "ScoringSettingsUpdate",
    # proposal
    "ServiceDetail", "TimelineItem", "ProposalIn", "ProposalOut",
    "ServiceItemIn", "ServiceItemOut", "TrackOpenIn", "TrackPingIn",
    "AnalyticsOut", "ProposalAcceptIn", "ProposalRejectIn",
    # finance
    "WalletIn", "WalletOut", "TransactionIn", "TransactionOut",
    "SubscriptionIn", "SubscriptionOut", "PaymentMethodIn", "PaymentMethodOut",
    "FinanceReportOut",
    # product
    "CategoryIn", "CategoryOut", "ProductIn", "ProductOut",
    "DynamicTemplateIn", "DynamicTemplateOut",
    # workspace
    "WorkspaceInitIn", "WorkspaceCellUpdate", "WorkspaceRowIn", "WorkspaceColumnIn",
    "WorkspaceColumnUpdate", "WorkspaceSheetUpdate",
    # board
    "LeadMin", "BoardCardCommentOut", "BoardCardChecklistOut", "BoardCardActivityOut", "BoardCardAttachmentOut",
    "BoardCardOut", "BoardColumnOut", "BoardOut", "BoardColumnIn", "BoardCardIn",
    "BoardCardUpdate", "MoveCardRequest", "BoardCardCommentIn", "BoardCardChecklistIn",
    # project
    "ProjectIn", "ProjectOut", "ClientNoteIn", "ClientNoteOut",
    "ProjectRiwayatIn", "ProjectRiwayatOut",
    # credential
    "CredentialFieldIn", "CredentialIn", "CredentialFieldOut", "CredentialOut",
    "CredentialUpdate",
    # document
    "DocumentIn", "DocumentOut", "BrandKitUpdate", "BrandAssetIn",
    "DocumentTemplateIn", "DocumentGenerateIn", "DocumentEmailIn", "InvoiceSequenceIn",
    "DocumentWorkflowUpdate", "DocumentDraftIn", "DocumentDraftOut",
    "DocumentEditIn", "DocumentVersionOut",
    # campaign
    "AdsCampaignIn", "AdsCampaignUpdate", "AdsCampaignOut",
    "BlastCampaignIn", "BlastCampaignOut", "FonnteWebhookIn",
    # content
    "ContentScheduleIn", "ContentScheduleUpdate", "ContentScheduleOut",
    "ContentProviderIn", "ContentProviderOut", "ContentSessionIn",
    "ContentSessionUpdate", "ContentSessionOut", "ContentGenerationOut",
    "ImageGenRequest", "CaptionGenRequest", "SeoArticleGenRequest", "CmsPublishRequest",
    # ai
    "AIModelIn", "AIModelOut", "AIProxyIn", "AIProxyOut", "ProviderConfigOut",
    # archive
    "ArchiveFolderIn", "ArchiveFolderUpdate", "ArchiveDocIn", "ArchiveDocUpdate",
    # office
    "OfficeChatAttachment", "OfficeChatRequest", "OfficeAgentCreate",
    "OfficeSoulUpdate", "OfficeEnvUpdate", "OfficeConfigUpdate",
    # tracking
    "TrackActivityBody", "ViewDurationIn",
    # admin
    "SettingsUpdate", "DataAdminBody",
]
