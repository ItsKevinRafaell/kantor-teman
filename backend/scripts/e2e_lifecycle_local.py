#!/usr/bin/env python3
"""E2E LOKAL scheduler lifecycle — bukti "1 lead gerak -> sequence jalan" tanpa prod.

Apa yang dilakukan:
  1. DB sqlite FILE BARU (e2e_lifecycle_local.db) — TIDAK menyentuh prod, bukan leads.db dev.
  2. Seed 1 lead status WA_Terkirim + proposal dibuat 72 jam lalu, tidak pernah di-view.
  3. Panggil process_outreach_lifecycle_states() — FUNGSI YANG SAMA yang dijadwalkan
     worker (feat/raka-e2e-scheduler-enable) tiap jam (job "lifecycle").
  4. Verifikasi: lead pindah ke "Follow Up" + baris AuditLog rule NO_CLICK_FOLLOWUP.

Blast TIDAK dipanggil (job blast butuh --allow-blast, default worker menolak).

Jalankan:
  cd backend && ./venv/bin/python scripts/e2e_lifecycle_local.py
Exit 0 = e2e pass.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

# Safety: tolak keras kalau ini bakal nyambung ke MySQL (prod/dev server).
_db_url_env = os.environ.get("DATABASE_URL", "")
if _db_url_env.startswith("mysql"):
    print("REFUSE: DATABASE_URL menunjuk MySQL. Script ini HANYA untuk sqlite lokal.", file=sys.stderr)
    raise SystemExit(2)

DB_PATH = BACKEND_DIR / "e2e_lifecycle_local.db"
if DB_PATH.exists():
    DB_PATH.unlink()

# Set env SEBELUM import app/model (engine dibaca saat import).
from cryptography.fernet import Fernet  # noqa: E402

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "e2e-local-jwt-secret-minimum-32-bytes-ok"
os.environ["ENV_FILE"] = ".env.test"
os.environ["ENABLE_BACKGROUND_SCHEDULER"] = "false"  # worker web tetap mati di test ini

from sqlalchemy.orm import sessionmaker  # noqa: E402

from models.base import Base, engine, log_audit  # noqa: E402
import models  # noqa: E402,F401  — register semua model
from models.lead import Lead, AuditLog  # noqa: E402
from models.proposal import Proposal  # noqa: E402
from app.constants import LeadStatus  # noqa: E402
from app.schedulers.outreach_machine import process_outreach_lifecycle_states  # noqa: E402

Base.metadata.create_all(bind=engine)
db = sessionmaker(bind=engine)()

now = datetime.now(timezone.utc)
old_72h = (now - timedelta(hours=72)).isoformat()

lead = Lead(
    business_name="E2E Scheduler Test — Kedai Kopi Raka",
    phone_number="+62812000000001",
    status=LeadStatus.WA_SENT,          # "WA Terkirim"
    is_archived=False,
)
db.add(lead)
db.commit()
db.refresh(lead)

proposal = Proposal(
    lead_id=lead.id,
    services_detail="Paket landing page + followup engine (E2E test)",
    total_price=500000,
    status="sent",
    created_at=old_72h,        # 72 jam lalu -> stagnant
    first_viewed_at=None,      # tidak pernah dibuka -> Rule 1 kena
    is_archived=False,
)
db.add(proposal)
db.commit()

pre_status = lead.status

# ── Jalankan fungsi yang sama dengan yang dijadwalkan worker ──────────────────
process_outreach_lifecycle_states(sessionmaker(bind=engine), Lead, Proposal, log_audit)

db.expire_all()
lead_after = db.get(Lead, lead.id)
audits = (
    db.query(AuditLog)
    .filter(AuditLog.table_name == "leads", AuditLog.record_id == str(lead.id))
    .all()
)
audit_details = [json.loads(a.details) if a.details else {} for a in audits]

result = {
    "lead_id": lead.id,
    "status_before": pre_status,
    "status_after": lead_after.status,
    "expected_status": LeadStatus.FOLLOW_UP,
    "audit_rows": len(audits),
    "audit_rules": [d.get("rule") for d in audit_details],
    "db": f"sqlite:///{DB_PATH.name} (local throwaway)",
    "blast_called": False,
}
print(json.dumps(result, ensure_ascii=False, indent=2))

passed = lead_after.status == LeadStatus.FOLLOW_UP and any(
    d.get("rule") == "NO_CLICK_FOLLOWUP" for d in audit_details
)
print(f"[E2E-LIFECYCLE] {'PASS' if passed else 'FAIL'}")
raise SystemExit(0 if passed else 1)
