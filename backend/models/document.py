import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


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
    # Legacy columns are still present in existing SQLite/MySQL tables.
    # Keep them mapped so inserts satisfy NOT NULL constraints while newer UI uses title/body.
    name = Column(String(255), nullable=False, default="")
    type = Column(String(50), nullable=False, default="document")
    content = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    url = Column(String(2000), nullable=True)
    tags = Column(Text, nullable=False, default="[]")
    status = Column(String(50), nullable=False, default="Draft")
    review_notes = Column(Text, nullable=True)
    approved_at = Column(String(255), nullable=True)
    rejected_at = Column(String(255), nullable=True)
    sent_at = Column(String(255), nullable=True)
    signed_at = Column(String(255), nullable=True)
    archived_at = Column(String(255), nullable=True)
    source_type = Column(String(50), nullable=True)
    source_id = Column(String(255), nullable=True)
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
    brand_name = Column(String(255), default="")
    tagline = Column(String(255), default="")
    phone = Column(String(50), default="")
    email = Column(String(255), default="")
    address = Column(Text, default="")
    logo = Column(Text, default="")


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
    status = Column(String(50), nullable=False, default="Draft")
    payment_status = Column(String(50), nullable=True)
    review_notes = Column(Text, nullable=True)
    approved_at = Column(String(255), nullable=True)
    rejected_at = Column(String(255), nullable=True)
    sent_at = Column(String(255), nullable=True)
    signed_at = Column(String(255), nullable=True)
    archived_at = Column(String(255), nullable=True)
    generated_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    generated_by = Column(String(255), nullable=True)
    template = relationship("DocumentTemplate", backref="generated_docs")


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_type = Column(String(50), nullable=False, default="monthly")
    target_type = Column(String(50), nullable=False, default="project")
    target_id = Column(String(255), nullable=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    service_type = Column(String(50), nullable=True)
    title = Column(String(500), nullable=False)
    period_start = Column(String(50), nullable=True)
    period_end = Column(String(50), nullable=True)
    month_number = Column(Integer, nullable=True)
    metrics_json = Column(Text, nullable=False, default="{}")
    evidence_json = Column(Text, nullable=False, default="{}")
    narrative_json = Column(Text, nullable=False, default="{}")
    public_slug = Column(String(255), nullable=True, unique=True, index=True)
    public_enabled = Column(Boolean, nullable=False, default=True)
    open_count = Column(Integer, nullable=False, default=0)
    first_viewed_at = Column(String(255), nullable=True)
    last_viewed_at = Column(String(255), nullable=True)
    max_duration_seconds = Column(Integer, nullable=False, default=0)
    generated_document_id = Column(String(36), ForeignKey("generated_documents.id"), nullable=True)
    status = Column(String(50), nullable=False, default="Draft")
    generated_by = Column(String(255), nullable=True)
    created_at = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(255), nullable=True)
    project = relationship("Project", foreign_keys=[project_id])
    lead = relationship("Lead", foreign_keys=[lead_id])
    generated_document = relationship("GeneratedDocument", foreign_keys=[generated_document_id])


class DocumentSequence(Base):
    __tablename__ = "document_sequences"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(String(255), nullable=False)
    template_type = Column(String(50), nullable=False)
    last_seq = Column(Integer, nullable=False, default=0)
