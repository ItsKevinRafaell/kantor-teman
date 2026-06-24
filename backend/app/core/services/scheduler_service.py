"""
Scheduler helpers — blast processing and follow-up sequences.
"""
import os
import json
import uuid
import random
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.config import FRONTEND_URL
from app.core.services.rate_limiter import check_simple_rate_limit
from models import (
    SystemSettings, SessionLocal,
    Lead, BlastCampaign, BlastMessage, DynamicTemplate,
    FollowUpSequence,
)
from app.core.whatsapp_provider import send_whatsapp_message
from app.core.services.cost_service import log_outreach_cost
from app.core.services.slug_service import generate_unique_slug


def _acquire_scheduler_lock(job_name: str, ttl_seconds: int) -> bool:
    db = SessionLocal()
    try:
        key = f"scheduler_lock:{job_name}"
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        updated = db.query(SystemSettings).filter(
            SystemSettings.key == key,
            SystemSettings.value < now.isoformat(),
        ).update({"value": expires_at}, synchronize_session=False)
        db.commit()
        if updated:
            return True
        if db.query(SystemSettings).filter(SystemSettings.key == key).first():
            return False
        try:
            db.add(SystemSettings(key=key, value=expires_at))
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
    finally:
        db.close()


def _run_async_job(coro):
    import asyncio as _asyncio
    if not _acquire_scheduler_lock(coro.__name__, 3500 if coro.__name__ == "scheduled_followup_processor" else 55):
        return
    try:
        _asyncio.run(coro())
    except Exception as exc:
        print(f"[SCHEDULER] {coro.__name__} failed: {exc}", flush=True)


def _generate_fallback_analysis(lead) -> dict:
    pain_points = []
    category = (lead.product_interest or "bisnis").lower()
    if lead.rating and lead.rating < 4:
        pain_points.append(f"Rating Google Maps {lead.business_name} saat ini hanya {lead.rating}/5 — calon pelanggan cenderung skip bisnis dengan rating di bawah 4.0 dan langsung pilih kompetitor.")
    elif not lead.rating or lead.rating == 0:
        pain_points.append(f"{lead.business_name} belum memiliki rating yang cukup di Google Maps — ini membuat calon pelanggan ragu dan memilih kompetitor yang sudah punya banyak review positif.")
    pain_points.append(f"Saat calon pelanggan mencari '{category}' di Google, bisnis tanpa optimasi digital akan tenggelam di halaman belakang — artinya ratusan calon pelanggan potensial setiap bulan tidak pernah tahu {lead.business_name} ada.")
    city = ""
    if lead.address:
        city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else lead.address
    if city:
        pain_points.append(f"Kompetitor di area {city} yang sudah teroptimasi secara digital sedang mengambil pelanggan yang seharusnya milik Anda setiap harinya — dan gap ini semakin lebar setiap bulan yang berlalu.")
    else:
        pain_points.append("Tanpa kehadiran digital yang kuat, bisnis Anda kehilangan peluang dari pelanggan yang mencari layanan Anda secara online setiap hari.")
    return {
        "analysis": f"Berdasakan audit digital yang kami lakukan terhadap {lead.business_name}, kami menemukan beberapa area kritis yang perlu segera ditangani untuk mencegah kehilangan pelanggan potensial ke kompetitor.",
        "pain_points": pain_points,
        "suggested_product": lead.product_interest or "SEO & Google Maps Optimization",
    }


def _build_addons_from_products(db: Session) -> str:
    from models import Product
    products = db.query(Product).filter(Product.is_active == True).all()
    addons = [{"id": p.id, "name": p.name, "price": p.base_price} for p in products]
    return json.dumps(addons)


async def process_pending_blasts():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).isoformat()
        pending = db.query(BlastCampaign).filter(
            BlastCampaign.status == "PENDING",
            BlastCampaign.scheduled_for <= now,
        ).all()
        for campaign in pending:
            claimed = db.query(BlastCampaign).filter(
                BlastCampaign.id == campaign.id,
                BlastCampaign.status == "PENDING",
            ).update({"status": "PROCESSING"}, synchronize_session=False)
            db.commit()
            if not claimed:
                continue
            db.refresh(campaign)
            try:
                criteria = json.loads(campaign.filter_criteria) if campaign.filter_criteria else {}
                query = db.query(Lead).filter(Lead.is_archived == False, Lead.do_not_contact == False)
                if criteria.get("status"):
                    query = query.filter(Lead.status == criteria["status"])
                if criteria.get("batch_name"):
                    query = query.filter(Lead.batch_name == criteria["batch_name"])
                if criteria.get("min_rating") and int(criteria["min_rating"]) > 0:
                    query = query.filter(Lead.rating >= int(criteria["min_rating"]))
                leads = query.all()

                whatsapp_config = send_whatsapp_message.__self__._config  # noqa
                from app.core.whatsapp_provider import _whatsapp_config
                whatsapp_config = _whatsapp_config(db)
                template = None
                if campaign.template_id:
                    template = db.query(DynamicTemplate).filter(DynamicTemplate.id == campaign.template_id).first()
                if not template:
                    templates = db.query(DynamicTemplate).filter(DynamicTemplate.type == "WA_BLAST", DynamicTemplate.is_active == True).all()
                    if templates:
                        template = random.choice(templates)
                sent = 0
                failed = 0
                for lead in leads:
                    report_slug = generate_unique_slug(db, lead.business_name)
                    from models import Proposal, LeadAnalysis, Product
                    existing_reports = db.query(Proposal).filter(
                        Proposal.lead_id == lead.id,
                        Proposal.status == "Report",
                    ).order_by(Proposal.created_at.desc()).all()
                    slug = report_slug
                    if not existing_reports:
                        from app.core.services.settings_service import _get_setting
                        existing_analysis = db.query(LeadAnalysis).filter(LeadAnalysis.lead_id == lead.id).order_by(LeadAnalysis.id.desc()).first()
                        if existing_analysis:
                            analysis = existing_analysis
                        else:
                            fallback = _generate_fallback_analysis(lead)
                            analysis = LeadAnalysis(
                                lead_id=lead.id,
                                analysis=fallback["analysis"],
                                pain_points=json.dumps(fallback["pain_points"]),
                                suggested_product=fallback["suggested_product"],
                                analyzed_at=datetime.now(timezone.utc).isoformat(),
                            )
                            db.add(analysis)
                            db.commit()
                        products = db.query(Product).filter(Product.is_active == True).all()
                        services = [{"name": p.name, "price": p.base_price, "features": (p.description or "").split("\n")} for p in products[:3]] if products else [{"name": "SEO & Google Maps", "price": 0, "features": ["Optimasi ranking Google", "Setup Google Business Profile"]}]
                        report = Proposal(
                            id=str(uuid.uuid4()),
                            lead_id=lead.id,
                            services_detail=json.dumps(services),
                            total_price=sum(s["price"] for s in services),
                            base_price=sum(s["price"] for s in services),
                            discount_price=round(sum(s["price"] for s in services) * (1 - float(_get_setting("proposal_discount_percent", "15")) / 100)),
                            discount_expires_at=None,
                            additional_options=None,
                            status="Report",
                            created_at=datetime.now(timezone.utc).isoformat(),
                            slug=slug,
                            faqs=json.dumps([
                                {"question": "Apakah audit ini gratis?", "answer": "Ya, audit digital ini 100% gratis dan tanpa kewajiban apapun."},
                                {"question": "Berapa lama sampai terlihat hasilnya?", "answer": "Dengan optimasi yang tepat, peningkatan visibilitas di Google bisa terlihat dalam 14-30 hari kerja pertama."},
                            ]),
                            selected_addons=_build_addons_from_products(db),
                            timeline_data=None,
                        )
                        db.add(report)
                        db.commit()
                    else:
                        slug = existing_reports[0].slug

                    report_link = f"{FRONTEND_URL}/r/{slug}"
                    if template:
                        product_name = criteria.get("product_category") or lead.product_interest or "layanan kami"
                        message = template.content.replace("{{client_name}}", lead.business_name).replace("{{business_name}}", lead.business_name).replace("{{product_name}}", product_name)
                    else:
                        message = f"Halo {lead.business_name}, kami menyiapkan audit digital singkat untuk bisnis Anda. Apakah kami boleh menjelaskan poin yang paling prioritas?\n\nLaporan ringkas: {report_link}"
                    message = message.replace("{{proposal_link}}", f"\n{report_link}\n")
                    result = await send_whatsapp_message(db, lead.phone_number, message, {
                        "lead_id": lead.id,
                        "campaign_id": campaign.id,
                        "template_id": template.id if template else None,
                        "batch_name": criteria.get("batch_name"),
                        "business_name": lead.business_name,
                    })
                    success = result.ok
                    db.add(BlastMessage(
                        id=str(uuid.uuid4()), campaign_id=campaign.id, lead_id=lead.id,
                        template_id=template.id if template else None,
                        phone_number=lead.phone_number,
                        sent_at=datetime.now(timezone.utc).isoformat(),
                        status="sent" if success else "failed",
                        error_message=None if success else (result.error or f"{result.provider} send failed"),
                    ))
                    if success:
                        lead.status = "WA Terkirim"
                        sent += 1
                    else:
                        failed += 1
                    db.commit()
                    await asyncio.sleep(whatsapp_config.blast_delay_seconds)
                campaign.sent_count = sent
                campaign.failed_count = failed
                campaign.status = "SUCCESS" if failed == 0 else "PARTIAL"
                log_outreach_cost(db, campaign.id, sent)
                db.commit()
            except Exception as exc:
                campaign.status = "FAILED"
                print(f"[SCHEDULED BLAST] campaign={campaign.id} failed: {exc}", flush=True)
                db.commit()
    finally:
        db.close()


async def scheduled_followup_processor():
    db = SessionLocal()
    try:
        enabled = db.query(SystemSettings).filter_by(key="followup_enabled").first()
        if not enabled or enabled.value != "true":
            return
        hour_setting = db.query(SystemSettings).filter_by(key="followup_hour").first()
        target_hour = int(hour_setting.value) if hour_setting and hour_setting.value else 9
        current_hour = datetime.now(timezone.utc).hour + 7
        if current_hour >= 24:
            current_hour -= 24
        if current_hour != target_hour:
            return
        now = datetime.now(timezone.utc)
        sequences = db.query(FollowUpSequence).filter(
            FollowUpSequence.status == "ACTIVE",
            FollowUpSequence.next_send_at <= now.isoformat(),
        ).all()

        for seq in sequences:
            lead = db.query(Lead).filter(Lead.id == seq.lead_id).first()
            if not lead:
                seq.status = "STOPPED"; seq.stopped_reason = "lead_not_found"; db.commit(); continue
            if lead.do_not_contact:
                seq.status = "STOPPED"; seq.stopped_reason = "opt_out"; db.commit(); continue
            template_ids = json.loads(seq.template_ids) if seq.template_ids else []
            delays = json.loads(seq.delays) if seq.delays else []
            if seq.current_step >= len(delays):
                seq.status = "COMPLETED"; db.commit(); continue
            message = None
            if template_ids and seq.current_step < len(template_ids):
                tmpl = db.query(DynamicTemplate).filter(DynamicTemplate.id == template_ids[seq.current_step]).first()
                if tmpl:
                    message = tmpl.content.replace("{{business_name}}", lead.business_name).replace("{{client_name}}", lead.business_name)
            if not message:
                followup_defaults = [
                    f"Halo {lead.business_name}, saya ingin follow up terkait laporan audit digital yang sudah saya kirimkan sebelumnya. Apakah ada pertanyaan yang bisa saya bantu jawab?",
                    f"Pak, saya notice laporan audit untuk {lead.business_name} sudah dibuka tapi belum ada respons. Apakah ada kendala atau pertanyaan? Saya siap bantu jelaskan lebih detail.",
                    f"Halo Pak, ini follow up terakhir dari saya untuk {lead.business_name}. Jika memang belum berminat saat ini, tidak masalah. Tapi perlu diingat, slot optimasi wilayah Anda terbatas dan kompetitor terus bergerak.",
                ]
                message = followup_defaults[min(seq.current_step, len(followup_defaults) - 1)]
            result = await send_whatsapp_message(db, lead.phone_number, message, {
                "lead_id": lead.id,
                "request_id": f"followup:{seq.id}:{seq.current_step}",
                "business_name": lead.business_name,
            })
            if not result.ok:
                continue
            seq.current_step += 1
            if seq.current_step >= len(delays):
                seq.status = "COMPLETED"; seq.next_send_at = None
            else:
                next_delay = delays[seq.current_step] if seq.current_step < len(delays) else 7
                seq.next_send_at = (now + timedelta(days=next_delay)).isoformat()
            db.commit()
    finally:
        db.close()
