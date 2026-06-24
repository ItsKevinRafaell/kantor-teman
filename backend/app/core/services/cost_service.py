"""
Cost logging for outreach and AI usage.
"""
from sqlalchemy.orm import Session

from app.core.config import USD_TO_IDR
from app.core.whatsapp_provider import get_whatsapp_cost_provider_id
from models import ProviderConfig, BlastCampaign


def log_outreach_cost(db: Session, campaign_id: str, messages_count: int):
    provider = db.query(ProviderConfig).filter_by(id=get_whatsapp_cost_provider_id(db)).first()
    if not provider:
        return
    cost = provider.price_per_unit_idr * messages_count
    provider.remaining_quota = max(0, (provider.remaining_quota or 0) - messages_count)
    campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
    if campaign:
        campaign.total_operational_cost_idr = (campaign.total_operational_cost_idr or 0) + cost
    db.commit()


def log_ai_cost(db: Session, campaign_id: str | None, model_name: str, input_tokens: int, output_tokens: int):
    provider = db.query(ProviderConfig).filter_by(id="9ROUTER").first()
    if not provider:
        return
    cost_usd = (provider.price_input_token_usd * input_tokens / 1000) + (provider.price_output_token_usd * output_tokens / 1000)
    cost_idr = cost_usd * USD_TO_IDR
    provider.remaining_quota = (provider.remaining_quota or 0) + cost_idr
    if campaign_id:
        campaign = db.query(BlastCampaign).filter_by(id=campaign_id).first()
        if campaign:
            campaign.total_operational_cost_idr = (campaign.total_operational_cost_idr or 0) + cost_idr
    db.commit()
