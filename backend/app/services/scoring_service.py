"""Lead scoring service with configurable weights and manual adjustment."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.constants import DEFAULT_SCORING_SETTINGS
from models import Lead, LeadActivityLog, LeadAnalysis, SystemSettings, log_audit


SCORING_SETTINGS_KEY = "lead_scoring_settings"


def get_scoring_settings(db: Optional[Session] = None) -> dict:
    settings = DEFAULT_SCORING_SETTINGS.copy()
    if not db:
        return settings
    row = db.query(SystemSettings).filter(SystemSettings.key == SCORING_SETTINGS_KEY).first()
    if not row or not row.value:
        return settings
    try:
        saved = json.loads(row.value)
        if isinstance(saved, dict):
            for key, value in saved.items():
                if key in settings:
                    settings[key] = int(value)
    except Exception:
        pass
    return settings


def save_scoring_settings(db: Session, updates: dict, actor: str) -> dict:
    settings = get_scoring_settings(db)
    for key, value in updates.items():
        if key not in settings:
            continue
        settings[key] = int(value)
    row = db.query(SystemSettings).filter(SystemSettings.key == SCORING_SETTINGS_KEY).first()
    if not row:
        row = SystemSettings(key=SCORING_SETTINGS_KEY, value=json.dumps(settings))
        db.add(row)
    else:
        row.value = json.dumps(settings)
    db.commit()
    log_audit(db, actor, "UPDATE", "system_settings", SCORING_SETTINGS_KEY, {"keys": list(updates.keys())})
    return settings


def calculate_lead_score_from_settings(
    lead: Lead,
    settings: Optional[dict] = None,
    has_ai_analysis: bool = False,
    report_signal: Optional[str] = None,
) -> tuple[int, dict]:
    weights = {**DEFAULT_SCORING_SETTINGS, **(settings or {})}
    score = int(weights["base_score"])
    breakdown: dict[str, int] = {"Skor dasar": int(weights["base_score"])}

    if lead.google_rating is not None:
        if lead.google_rating >= 4.5:
            score += weights["google_rating_high"]
            breakdown["Rating Google >=4.5"] = weights["google_rating_high"]
        elif lead.google_rating >= 4.0:
            score += weights["google_rating_medium"]
            breakdown["Rating Google 4.0-4.4"] = weights["google_rating_medium"]
        elif lead.google_rating >= 3.5:
            score += weights["google_rating_low"]
            breakdown["Rating Google 3.5-3.9"] = weights["google_rating_low"]
        else:
            score += weights["google_rating_bad"]
            breakdown["Rating Google <3.5"] = weights["google_rating_bad"]

    review_count = lead.review_count or 0
    if review_count > 100:
        score += weights["reviews_high"]
        breakdown["Review >100"] = weights["reviews_high"]
    elif review_count >= 20:
        score += weights["reviews_medium"]
        breakdown["Review 20-100"] = weights["reviews_medium"]

    has_website = bool(lead.website_url)
    product_interest = (lead.product_interest or "").lower()
    if has_website:
        if any(k in product_interest for k in ["seo", "maintenance"]):
            score += weights["website_for_seo"]
            breakdown["Punya website untuk SEO/Maintenance"] = weights["website_for_seo"]
        else:
            score += weights["website_not_needed"]
            breakdown["Sudah punya website"] = weights["website_not_needed"]
    elif "web" in product_interest:
        score += weights["no_website_for_web"]
        breakdown["Belum punya website untuk Web"] = weights["no_website_for_web"]

    batch_name = (lead.batch_name or "").lower()
    if "web form" in batch_name:
        score += weights["warm_source"]
        breakdown["Sumber hangat"] = weights["warm_source"]
    elif any(k in batch_name for k in ["scrape", "maps", "gmaps", "·"]):
        score += weights["cold_source"]
        breakdown["Sumber scrape dingin"] = weights["cold_source"]

    if lead.status == "Replied":
        score += weights["replied"]
        breakdown["Membalas WA"] = weights["replied"]
    elif lead.status in ("Contacted", "WA Terkirim"):
        score += weights["contacted_no_reply"]
        breakdown["Sudah dihubungi belum balas"] = weights["contacted_no_reply"]

    address = (lead.address or "").lower()
    if any(city in address for city in ["jakarta", "surabaya", "bandung", "bali", "denpasar"]):
        score += weights["tier_one_city"]
        breakdown["Kota prioritas"] = weights["tier_one_city"]

    name_upper = (lead.business_name or "").upper()
    if any(k in name_upper for k in ["PT ", "PT.", " CV ", "CV.", "GROUP", "GRUP"]):
        score += weights["company_signal"]
        breakdown["Sinyal badan usaha"] = weights["company_signal"]

    if has_ai_analysis:
        score += weights["ai_analysis"]
        breakdown["Analisis AI tersedia"] = weights["ai_analysis"]

    report_points = {
        "report_opened": weights["report_opened"],
        "report_started_reading": weights["report_started_reading"],
        "report_reading_seriously": weights["report_reading_seriously"],
        "report_hot_action": weights["report_hot_action"],
    }
    if report_signal in report_points:
        score += report_points[report_signal]
        breakdown["Engagement laporan"] = report_points[report_signal]

    adjustment = int(getattr(lead, "score_adjustment", 0) or 0)
    if adjustment:
        score += adjustment
        breakdown["Adjustment manual"] = adjustment

    return max(0, min(100, int(score))), breakdown


def recalculate_lead_score_with_context(db: Session, lead: Lead) -> tuple[int, dict]:
    has_ai_analysis = db.query(LeadAnalysis.id).filter(LeadAnalysis.lead_id == lead.id).first() is not None
    signal_priority = [
        "report_hot_action",
        "report_reading_seriously",
        "report_started_reading",
        "report_opened",
    ]
    signal = None
    for candidate in signal_priority:
        exists = db.query(LeadActivityLog.id).filter(
            LeadActivityLog.lead_id == lead.id,
            LeadActivityLog.activity_type == candidate,
        ).first()
        if exists:
            signal = candidate
            break
    score, breakdown = calculate_lead_score_from_settings(
        lead,
        get_scoring_settings(db),
        has_ai_analysis=has_ai_analysis,
        report_signal=signal,
    )
    lead.lead_score = score
    lead.score_updated_at = datetime.now(timezone.utc).isoformat()
    return score, breakdown


def set_manual_score_adjustment(
    db: Session,
    lead_id: int,
    adjustment: int,
    reason: Optional[str],
    actor: str,
) -> tuple[int, dict]:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise ValueError("Lead tidak ditemukan")
    lead.score_adjustment = int(adjustment)
    lead.score_adjustment_reason = reason or None
    score, breakdown = recalculate_lead_score_with_context(db, lead)
    db.commit()
    log_audit(db, actor, "UPDATE", "leads", lead_id, {
        "field": "score_adjustment",
        "adjustment": adjustment,
        "reason": reason,
        "score": score,
    })
    return score, breakdown
