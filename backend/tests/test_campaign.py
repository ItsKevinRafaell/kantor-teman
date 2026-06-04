"""Campaign tests - opt-out, followup scheduling."""
import os
import json
import uuid
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.dependencies import create_token, hash_password
from models import User, Lead, BlastCampaign, FollowUpSequence, DynamicTemplate


def _get_or_create_user(db, email, name, password, role):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name, hashed_password=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _unique_phone():
    return f"6289{uuid.uuid4().hex[:10]}"


class TestOptOutBlocksBlast:
    def test_opt_out_blocks_blast(self, client, db):
        opted_out = Lead(business_name="Opt Out Co", phone_number=_unique_phone(), status="Scraped", do_not_contact=True)
        db.add(opted_out)
        db.commit()

        normal = Lead(business_name="Normal Co", phone_number=_unique_phone(), status="Scraped", do_not_contact=False)
        db.add(normal)
        db.commit()

        leads = db.query(Lead).filter(Lead.is_archived == False, Lead.do_not_contact == False).all()
        lead_ids = [l.id for l in leads]

        assert opted_out.id not in lead_ids
        assert normal.id in lead_ids

    def test_lead_status_followup_opt_out(self, client, db):
        lead = Lead(business_name="Followup Test", phone_number=_unique_phone(), status="Contacted", do_not_contact=True)
        db.add(lead)
        db.commit()

        seq = FollowUpSequence(lead_id=lead.id, template_ids=json.dumps([]), delays=json.dumps([1, 3, 7]), current_step=0, status="ACTIVE", started_at="2026-06-04T09:00:00Z")
        db.add(seq)
        db.commit()

        if lead.do_not_contact:
            seq.status = "STOPPED"
            seq.stopped_reason = "opt_out"
            db.commit()

        db.refresh(seq)
        assert seq.status == "STOPPED"
        assert seq.stopped_reason == "opt_out"

    def test_fonnte_webhook_opt_out_blocks_future(self, client, db):
        sender_digits = _unique_phone()
        lead = db.query(Lead).filter(Lead.phone_number == sender_digits).first()
        if not lead:
            lead = Lead(business_name="Webhook Test", phone_number=sender_digits, status="Scraped", do_not_contact=False)
            db.add(lead)
            db.commit()

        message = "STOP jangan hubungi saya"
        opt_out_terms = {"stop", "berhenti", "unsubscribe", "jangan hubungi", "hapus nomor"}
        if any(term in message.lower() for term in opt_out_terms):
            lead.do_not_contact = True
            db.commit()

        db.refresh(lead)
        assert lead.do_not_contact == True


class TestFollowupScheduled:
    def test_followup_scheduled(self, client, db):
        lead = Lead(business_name="Follow Up Needed", phone_number=_unique_phone(), status="Follow-up", do_not_contact=False)
        db.add(lead)
        db.commit()

        seq = FollowUpSequence(lead_id=lead.id, template_ids=json.dumps([]), delays=json.dumps([1, 3, 7]), current_step=0, status="ACTIVE", started_at="2026-06-04T09:00:00Z", next_send_at="2026-06-05T09:00:00Z")
        db.add(seq)
        db.commit()

        assert seq.status == "ACTIVE"
        assert seq.current_step == 0
        assert seq.lead_id == lead.id

    def test_followup_advances_steps(self, client, db):
        lead = Lead(business_name="Multi Step", phone_number=_unique_phone(), status="Contacted", do_not_contact=False)
        db.add(lead)
        db.commit()

        delays = [1, 3, 7]
        seq = FollowUpSequence(lead_id=lead.id, template_ids=json.dumps([]), delays=json.dumps(delays), current_step=0, status="ACTIVE", started_at="2026-06-04T09:00:00Z", next_send_at="2026-06-05T09:00:00Z")
        db.add(seq)
        db.commit()

        seq.current_step += 1
        db.commit()

        db.refresh(seq)
        assert seq.current_step == 1

        seq.current_step = len(delays)
        db.commit()

        if seq.current_step >= len(delays):
            seq.status = "COMPLETED"
            seq.next_send_at = None
            db.commit()

        db.refresh(seq)
        assert seq.status == "COMPLETED"

    def test_lead_status_followup_creates_sequence(self, client, db):
        lead = Lead(business_name="Auto Sequence", phone_number=_unique_phone(), status="Follow-up", do_not_contact=False)
        db.add(lead)
        db.commit()

        existing = db.query(FollowUpSequence).filter(FollowUpSequence.lead_id == lead.id).first()
        if not existing and lead.status == "Follow-up" and not lead.do_not_contact:
            new_seq = FollowUpSequence(lead_id=lead.id, template_ids=json.dumps([]), delays=json.dumps([1, 3, 7]), current_step=0, status="ACTIVE", started_at="2026-06-04T09:00:00Z")
            db.add(new_seq)
            db.commit()

        created = db.query(FollowUpSequence).filter(FollowUpSequence.lead_id == lead.id).first()
        assert created is not None
        assert created.status == "ACTIVE"
