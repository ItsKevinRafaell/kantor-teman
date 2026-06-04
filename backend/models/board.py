import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


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
