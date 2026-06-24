"""
WhatsApp (Fonnte) messaging — sync and async variants.
"""
import httpx
from sqlalchemy.orm import Session

from models import SystemSettings


def get_fonnte_token(db: Session) -> str:
    row = db.query(SystemSettings).filter_by(key="fonnte_token").first()
    return (row.value or "") if row else ""


async def send_fonnte_message(phone: str, message: str, token: str) -> bool:
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": token},
                data={"target": phone, "message": message, "delay": "5"},
            )
            return resp.status_code == 200
    except Exception:
        return False


def _send_fonnte_sync(phone: str, message: str, token: str, _httpx) -> bool:
    if not token:
        return False
    try:
        with _httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": token},
                data={"target": phone, "message": message, "delay": "5"},
            )
            return resp.status_code == 200 and resp.json().get("status") != False
    except Exception as e:
        print(f"[FONNTE ERROR] {e}", flush=True)
        return False
