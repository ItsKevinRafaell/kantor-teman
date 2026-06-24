"""Chat-related Pydantic models."""
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = ""
    session_id: Optional[str] = None
    attachments: Optional[list] = None
    room_key: Optional[str] = None
    topic_title: Optional[str] = None
    metadata: Optional[dict] = None


class TelegramMirrorMessage(BaseModel):
    message: str
    profiles: Optional[list[str]] = None
    room_key: Optional[str] = None
    session_id: Optional[str] = None
    chat_id: Optional[str] = None
    message_thread_id: Optional[str] = None
    topic_title: Optional[str] = None
    attachments: Optional[list] = None


class RunApproval(BaseModel):
    choice: str


class ApprovalDecision(BaseModel):
    decision: str


class ForwardRequest(BaseModel):
    source_profile: Optional[str] = None
    target_profile: str
    messages: list[str]


class QueueStatus(BaseModel):
    run_id: str
    queue_id: str
    status: str
    session_id: str
    profile: str
    response: str = ""
    output: str = ""
    events: list = []
    next_event: int = 0
    queued_message_count: int = 0
    queued_until: str = ""
    seconds_remaining: int = 0
    error: Optional[str] = None
