import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


# Workspace Klien Models
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
