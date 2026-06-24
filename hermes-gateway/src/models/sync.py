"""Sync/timeline-related Pydantic models."""
from typing import Optional

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    id: int
    profile: str
    kind: str
    role: str
    content: str
    metadata: dict = {}
    source: str
    session_id: Optional[str] = None
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    message_thread_id: Optional[str] = None
    topic_title: Optional[str] = None
    room_key: Optional[str] = None
    chat_type: Optional[str] = None
    created_at: str = ""


class TimelineResponse(BaseModel):
    events: list[TimelineEvent]
    next_cursor: int = 0
    has_more: bool = False
    pending_approval_count: int = 0


class TopicBinding(BaseModel):
    chat_id: str
    message_thread_id: str
    topic_title: str
    room_key: str


class RoomSummary(BaseModel):
    id: str
    room_key: str
    title: str
    topic_title: Optional[str] = None
    chat_id: str = ""
    session_id: Optional[str] = None
    message_thread_id: Optional[str] = None
    chat_type: Optional[str] = None
    profiles: list[str] = []
    last_event_id: int = 0
    last_event_at: str = ""
    source: str = "profile"


class SyncState(BaseModel):
    last_message_id: int = 0
    completed_at: Optional[float] = None
