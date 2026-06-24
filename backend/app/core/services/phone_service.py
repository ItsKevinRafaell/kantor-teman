"""
Phone number normalization utilities.
"""
import re
from typing import Optional


def normalize_phone(phone: str) -> Optional[str]:
    """Normalize to 62xx format (for WA API)."""
    if not phone:
        return None
    raw = str(phone).strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif not digits.startswith("62"):
        digits = "62" + digits
    return digits


def normalize_phone_storage(phone: str) -> Optional[str]:
    """Normalize to 08xx format (for storage in DB)."""
    if not phone:
        return None
    raw = str(phone).strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("62"):
        digits = "0" + digits[2:]
    elif not digits.startswith("0"):
        digits = "0" + digits
    return digits


def make_wa_url(phone_digits: str) -> str:
    return f"https://wa.me/{phone_digits}"
