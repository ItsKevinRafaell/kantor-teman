"""
Google Calendar sync.
"""
import os
import json
from datetime import datetime, timedelta

from app.core.config import (
    GOOGLE_CALENDAR_ID,
    GOOGLE_SERVICE_ACCOUNT_FILE,
)
from app.core.services.settings_service import _get_setting


def _get_google_calendar_service():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        scopes = ["https://www.googleapis.com/auth/calendar"]
        sa_json = _get_setting("google_service_account_json", GOOGLE_SERVICE_ACCOUNT_JSON)
        if sa_json:
            info = json.loads(sa_json)
            credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        elif GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
            credentials = service_account.Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes)
        else:
            return None
        return build("calendar", "v3", credentials=credentials)
    except Exception:
        return None


def _build_google_calendar_event_body(title: str, date_value: str) -> dict:
    start_date = datetime.fromisoformat(str(date_value)[:10]).date()
    end_date = start_date + timedelta(days=1)
    return {
        "summary": title,
        "start": {"date": start_date.isoformat()},
        "end": {"date": end_date.isoformat()},
    }


def sync_to_google_calendar(title: str, date: str, event_id: str | None = None) -> str | None:
    service = _get_google_calendar_service()
    if not service:
        return event_id

    calendar_id = _get_setting("google_calendar_id", GOOGLE_CALENDAR_ID)
    if not calendar_id:
        return event_id

    try:
        event_body = _build_google_calendar_event_body(title, date)
        if event_id:
            service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
            return event_id
        result = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return result.get("id")
    except Exception:
        return event_id
