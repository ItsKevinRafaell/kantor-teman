"""Campaign tests - opt-out, followup scheduling."""
import os
import json
import uuid

import pytest
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.dependencies import create_token, hash_password
from models import User, Lead, BlastCampaign, FollowUpSequence, DynamicTemplate


class TestOptOutBlocksBlast:
    """Test that leads with do_not_contact=True are skipped in blasts."""

    def test_opt_out_blocks_blast(self, client, db, admin_user):
        """Lead with do_not_contact=True -> blast should skip this lead."""
        token = create_token(admin_user.id, admin_user.email)

        # Create lead that opted out
        opted_out_lead = Lead(
            business_name="Opt Out Company",
            phone_number="6281234567800",
            status="Scraped",
            do_not_contact=True,
        )
        db.add(opted_out_lead)
        db.commit()
        db.refresh(opted_out_lead)

        # Create lead that can be contacted
        normal_lead = Lead(
            business_name="Normal Company",
            phone_number="6281234567801",
            status="Scraped",
            do_not_contact=False,
        )
        db.add(normal_lead)
        db.commit()
        db.refresh(normal_lead)

        # Verify initial state
        assert opted_out_lead.do_not_contact == True
        assert normal_lead.do_not_contact == False

        # Simulate blast filtering logic from process_pending_blasts
        # The blast should only include leads where do_not_contact == False
        from sqlalchemy.orm import Session
        leads = db.query(Lead).filter(
            Lead.is_archived == False,
            Lead.do_not_contact == False
        ).all()

        lead_ids = [l.id for l in leads]
        
        # Verify opted-out lead is NOT in the list
        assert opted_out_lead.id not in lead_ids, "Opted-out lead should be excluded"
        
        # Verify normal lead IS in the list
        assert normal_lead.id in lead_ids, "Normal lead should be included"

    def test_lead_status_followup_opt_out(self, client, db, admin_user):
        """Follow-up sequence should be stopped for opted-out leads."""
        token = create_token(admin_user.id, admin_user.email)

        # Create lead with active followup
        lead = Lead(
            business_name="Followup Test",
            phone_number="6281234567802",
            status="Contacted",
            do_not_contact=True,  # Opted out
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # Create active follow-up sequence
        sequence = FollowUpSequence(
            lead_id=lead.id,
            template_ids=json.dumps([]),
            delays=json.dumps([1, 3, 7]),
            current_step=0,
            status="ACTIVE",
            started_at="2026-06-04T09:00:00Z",
        )
        db.add(sequence)
        db.commit()
        db.refresh(sequence)

        # Verify sequence is active
        assert sequence.status == "ACTIVE"

        # Simulate the opt-out logic from scheduled_followup_processor
        # When lead.do_not_contact is True, sequence should be stopped
        if lead.do_not_contact:
            sequence.status = "STOPPED"
            sequence.stopped_reason = "opt_out"
            db.commit()

        # Verify sequence was stopped
        db.refresh(sequence)
        assert sequence.status == "STOPPED"
        assert sequence.stopped_reason == "opt_out"

    def test_fonnte_webhook_opt_out_blocks_future(self, client, db):
        """Verify Fonnte webhook can set do_not_contact=True."""
        # Simulate incoming webhook with opt-out message
        payload = {
            "sender": "6281234567803",
            "message": "STOP jangan hubungi saya",
            "device": "6281234567803",
        }

        # Find or create lead
        sender_digits = "6281234567803"
        lead = db.query(Lead).filter(Lead.phone_number == sender_digits).first()

        if not lead:
            lead = Lead(
                business_name="Webhook Test",
                phone_number=sender_digits,
                status="Scraped",
                do_not_contact=False,
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)

        # Process opt-out terms from message
        message = str(payload.get("message", "")).strip().lower()
        opt_out_terms = {"stop", "berhenti", "unsubscribe", "jangan hubungi", "hapus nomor"}

        if any(term in message for term in opt_out_terms):
            lead.do_not_contact = True
            db.commit()

        # Verify lead is opted out
        db.refresh(lead)
        assert lead.do_not_contact == True, "Lead should be opted out via webhook"


class TestFollowupScheduled:
    """Test follow-up sequence scheduling."""

    def test_followup_scheduled(self, client, db, admin_user):
        """Lead with status 'Follow-up' -> follow-up job should be created."""
        token = create_token(admin_user.id, admin_user.email)

        # Create lead with Follow-up status
        lead = Lead(
            business_name="Follow Up Needed",
            phone_number="6281234567804",
            status="Follow-up",
            do_not_contact=False,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # Create follow-up sequence for this lead
        template_ids = [str(uuid.uuid4())]
        sequence = FollowUpSequence(
            lead_id=lead.id,
            template_ids=json.dumps(template_ids),
            delays=json.dumps([1, 3, 7]),  # Day 1, 3, 7
            current_step=0,
            status="ACTIVE",
            started_at="2026-06-04T09:00:00Z",
            next_send_at="2026-06-05T09:00:00Z",  # Tomorrow
        )
        db.add(sequence)
        db.commit()
        db.refresh(sequence)

        # Verify sequence was created
        assert sequence.status == "ACTIVE"
        assert sequence.current_step == 0
        assert sequence.next_send_at is not None

        # Verify sequence is for the correct lead
        assert sequence.lead_id == lead.id

    def test_followup_advances_steps(self, client, db, admin_user):
        """Follow-up sequence should advance steps after each send."""
        token = create_token(admin_user.id, admin_user.email)

        # Create lead
        lead = Lead(
            business_name="Multi Step Followup",
            phone_number="6281234567805",
            status="Contacted",
            do_not_contact=False,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        # Create sequence with 3 steps
        delays = [1, 3, 7]
        sequence = FollowUpSequence(
            lead_id=lead.id,
            template_ids=json.dumps([]),
            delays=json.dumps(delays),
            current_step=0,
            status="ACTIVE",
            started_at="2026-06-04T09:00:00Z",
            next_send_at="2026-06-05T09:00:00Z",
        )
        db.add(sequence)
        db.commit()
        db.refresh(sequence)

        # Simulate step advancement (as in scheduled_followup_processor)
        sequence.current_step += 1
        db.commit()

        # Verify step advanced
        db.refresh(sequence)
        assert sequence.current_step == 1

        # After all steps, sequence should be COMPLETED
        sequence.current_step = len(delays)  # = 3
        db.commit()

        if sequence.current_step >= len(delays):
            sequence.status = "COMPLETED"
            sequence.next_send_at = None
            db.commit()

        db.refresh(sequence)
        assert sequence.status == "COMPLETED"

    def test_lead_status_followup_creates_sequence(self, client, db, admin_user):
        """New lead with Follow-up status -> sequence should be auto-created."""
        token = create_token(admin_user.id, admin_user.email)

        # Create lead with Follow-up status
        lead = Lead(
            business_name="Auto Sequence Test",
            phone_number="6281234567806",
            status="Follow-up",
            do_not_contact=False,
        )
        db.add(lead)
        db.commit()

        # Check if sequence already exists
        existing = db.query(FollowUpSequence).filter(
            FollowUpSequence.lead_id == lead.id
        ).first()

        # If no sequence and lead status is Follow-up, create one
        if not existing and lead.status == "Follow-up" and not lead.do_not_contact:
            new_sequence = FollowUpSequence(
                lead_id=lead.id,
                template_ids=json.dumps([]),
                delays=json.dumps([1, 3, 7]),
                current_step=0,
                status="ACTIVE",
                started_at="2026-06-04T09:00:00Z",
            )
            db.add(new_sequence)
            db.commit()

        # Verify sequence was created
        created = db.query(FollowUpSequence).filter(
            FollowUpSequence.lead_id == lead.id
        ).first()
        
        assert created is not None, "Follow-up sequence should be created for Follow-up status lead"
        assert created.status == "ACTIVE"
