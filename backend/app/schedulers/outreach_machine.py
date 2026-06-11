"""
Outreach Lifecycle State-Machine
Scheduler yang berjalan berkala (tiap 1 jam) untuk mendeteksi stagnansi aktivitas
dan memindahkan status Lead secara otomatis berdasarkan aturan pipeline penjualan.
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.constants import LeadStatus

logger = logging.getLogger("outreach_machine")
logger.setLevel(logging.INFO)


def process_outreach_lifecycle_states(SessionLocal, Lead, Proposal, log_audit):
    """
    Fungsi utama state-machine yang dipanggil oleh scheduler setiap 1 jam.
    Memindai database Lead & Proposal untuk mendeteksi stagnansi.
    """
    db: Session = SessionLocal()
    now = datetime.now(timezone.utc)
    transitions_count = 0

    try:
        # ==================================================================
        # RULE 1: No Click Follow-up
        # Status 'BLASTED' + lebih dari 48 jam tanpa aktivitas klik report
        # → Pindahkan ke 'FOLLOWUP_QUEUE'
        # ==================================================================
        threshold_48h = now - timedelta(hours=48)

        blasted_leads = db.query(Lead).filter(
            Lead.status.in_(["BLASTED", LeadStatus.WA_SENT]),
            Lead.is_archived == False,
        ).all()

        for lead in blasted_leads:
            # Cek apakah ada proposal yang sudah di-view (first_viewed_at terisi)
            proposal = db.query(Proposal).filter(
                Proposal.lead_id == lead.id,
                Proposal.first_viewed_at.isnot(None),
            ).first()

            # Jika sudah ada yang di-view, skip (mereka sudah klik)
            if proposal:
                continue

            # Cek waktu terakhir update — gunakan created_at proposal sebagai proxy
            latest_proposal = db.query(Proposal).filter(
                Proposal.lead_id == lead.id,
            ).order_by(Proposal.created_at.desc()).first()

            if latest_proposal and latest_proposal.created_at:
                try:
                    created = datetime.fromisoformat(latest_proposal.created_at.replace("Z", "+00:00"))
                    if created < threshold_48h:
                        old_status = lead.status
                        lead.status = LeadStatus.FOLLOW_UP
                        log_audit(db, "SYSTEM_SCHEDULER", "UPDATE", "leads", lead.id, {
                            "rule": "NO_CLICK_FOLLOWUP",
                            "old_status": old_status,
                            "new_status": LeadStatus.FOLLOW_UP,
                            "stagnant_hours": round((now - created).total_seconds() / 3600, 1),
                        })
                        transitions_count += 1
                        logger.info(f"[Rule 1] Lead #{lead.id} ({lead.business_name}): masuk Follow Up")
                except (ValueError, TypeError):
                    continue

        # ==================================================================
        # RULE 2: Viewed but No Contact (Stagnant)
        # Status 'REPORT_VIEWED' atau 'HOT_PROSPECT' + first_viewed_at > 24 jam
        # + belum CONTACTED/CLOSED
        # → Pindahkan ke 'WARM_STAGNANT'
        # ==================================================================
        threshold_24h = now - timedelta(hours=24)

        viewed_leads = db.query(Lead).filter(
            Lead.status.in_(["REPORT_VIEWED", "HOT_PROSPECT", LeadStatus.REPORT_OPENED, LeadStatus.STARTED_READING, LeadStatus.READING_SERIOUSLY, LeadStatus.WARM_PROSPECT, LeadStatus.HOT_PROSPECT]),
            Lead.is_archived == False,
        ).all()

        for lead in viewed_leads:
            # Cari proposal dengan first_viewed_at terisi
            proposal = db.query(Proposal).filter(
                Proposal.lead_id == lead.id,
                Proposal.first_viewed_at.isnot(None),
            ).first()

            if not proposal or not proposal.first_viewed_at:
                continue

            try:
                first_view = datetime.fromisoformat(proposal.first_viewed_at.replace("Z", "+00:00"))
                if first_view < threshold_24h:
                    old_status = lead.status
                    lead.status = LeadStatus.FOLLOW_UP
                    log_audit(db, "SYSTEM_SCHEDULER", "UPDATE", "leads", lead.id, {
                        "rule": "VIEWED_NO_CONTACT_STAGNANT",
                        "old_status": old_status,
                        "new_status": LeadStatus.FOLLOW_UP,
                        "first_viewed_at": proposal.first_viewed_at,
                        "stagnant_hours": round((now - first_view).total_seconds() / 3600, 1),
                    })
                    transitions_count += 1
                    logger.info(f"[Rule 2] Lead #{lead.id} ({lead.business_name}): {old_status} → {LeadStatus.FOLLOW_UP}")
            except (ValueError, TypeError):
                continue

        if transitions_count > 0:
            db.commit()
            logger.info(f"[Outreach Machine] Selesai: {transitions_count} transisi status diproses.")
        else:
            logger.info("[Outreach Machine] Selesai: Tidak ada transisi status yang diperlukan.")

    except Exception as e:
        db.rollback()
        logger.error(f"[Outreach Machine] Error: {e}")
    finally:
        db.close()
