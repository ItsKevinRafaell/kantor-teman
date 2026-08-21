import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from .base import Base


class Project(Base):
    __tablename__ = "projects"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    # P0-1: satu proposal maksimal satu project. UNIQUE mencegah double-accept
    # race membuat 2 project untuk proposal yang sama.
    proposal_id = Column(String(36), ForeignKey("proposals.id"), nullable=True, unique=True, index=True)
    # Opsi B (product-driven) Tahap 1: relasi project -> product katalog.
    # Nullable + ON DELETE SET NULL supaya project lama (tanpa product) tetap valid
    # dan hapus product tidak menghapus project. Logika report/proposal/kontrak
    # yang memanfaatkan relasi ini menyusul di tahap berikutnya.
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)  # FIXED / RETAINER
    status = Column(String(255), default="ACTIVE", nullable=False)  # ACTIVE / COMPLETED / HOLD
    nominal = Column(Float, nullable=False, default=0)
    start_date = Column(String(255), nullable=True)
    end_date = Column(String(255), nullable=True)
    color = Column(String(50), nullable=True, default="gray")
    is_archived = Column(Boolean, default=False, nullable=False)
    service_type = Column(String(50), nullable=True)
    contract_months = Column(Integer, nullable=True, default=1)
    dp_percent = Column(Float, nullable=True)
    monthly_invoice_enabled = Column(Boolean, default=False, nullable=False)
    next_invoice_date = Column(String(255), nullable=True)
    completed_at = Column(String(255), nullable=True)
    lead = relationship("Lead", foreign_keys=[lead_id])
    # Opsi B Tahap 1: akses katalog product dari project (read-only convenience).
    product = relationship("Product", foreign_keys=[product_id])
    # Add-on line items yang menempel pada project ini.
    addons = relationship(
        "ProjectAddon",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


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


class ProjectRiwayat(Base):
    __tablename__ = "project_riwayat"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(String(255), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    actor = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # STATUS / INVOICE / NOTE / FILE / MILESTONE / OTHER
    content = Column(Text, nullable=False)
    attachments = Column(Text, nullable=True)  # JSON list of file URLs
    project = relationship(
        "Project",
        backref=backref("riwayat", passive_deletes=True, cascade="all, delete-orphan"),
    )


class ProjectAddon(Base):
    """Opsi B (product-driven) Tahap 1 — add-on line item yang menempel pada project.

    Tabel baru (normalisasi) menggantikan add-on yang sebelumnya cuma disimpan
    sebagai JSON free-text di proposals.selected_addons. Menyimpan snapshot
    name/price supaya add-on tetap konsisten meski product katalog diedit/dihapus.
    Logika report/proposal/kontrak yang membaca tabel ini menyusul di tahap
    berikutnya — Tahap 1 HANYA schema.
    """

    __tablename__ = "project_addons"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Opsional: add-on boleh berasal dari katalog product, boleh custom/manual.
    # ON DELETE SET NULL supaya hapus product tidak menghapus baris add-on
    # (snapshot name/price tetap dipertahankan).
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)  # snapshot nama add-on
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False, default=0)  # snapshot harga satuan
    quantity = Column(Integer, nullable=False, default=1)
    is_recurring = Column(Boolean, default=False, nullable=False)  # retainer/bulanan vs one-off
    created_at = Column(
        String(255),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    project = relationship("Project", back_populates="addons")
    product = relationship("Product", foreign_keys=[product_id])
