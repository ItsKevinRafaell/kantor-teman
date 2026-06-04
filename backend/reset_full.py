"""
FULL RESET: Hapus SEMUA data kecuali users, system_settings, provider_configs.
Auto-jalankan seed.py setelah reset.

PERTAHANKAN:
  - users (akun login)
  - system_settings (API keys, config)
  - provider_configs (Fonnte, AI providers)
  - ai_models (model registry)

HAPUS SEMUA:
  - leads, contacts, proposals
  - boards, board_*, projects
  - chat_*, content_*
  - documents, client_*
  - blast_campaigns, ads_campaigns, content_schedules
  - lead_activity_logs, lead_analyses, scrape_history
  - reengagement_alerts, followup_sequences
  - audit_logs, message_templates, service_items
  - categories, products, dynamic_templates (dihapus, akan di-reseed)
  - wallets, transactions, subscriptions

SETELAH HAPUS:
  - Auto-jalankan seed_data() dari main.py untuk basic seed
  - Jalankan seed.py manual kalau perlu data demo

Jalankan: python reset_full.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from main import (
    SessionLocal, seed_data,
    Lead, Contact, Proposal, ScrapeHistory, LeadActivityLog, LeadAnalysis,
    Project, Board, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity,
    BlastCampaign, FollowUpSequence, ReengagementAlert, AdsCampaign,
    ContentSession, ContentGeneration, ContentSchedule,
    Document, DocumentFolder,
    ClientNote, ClientCredential, ClientDocument,
    MessageTemplate, ServiceItem, AuditLog,
    Category, Product, DynamicTemplate,
    Wallet, Transaction, Subscription,
    ProposalAnalytics,
)

print("=" * 60)
print("FULL RESET — Hapus semua data, pertahankan config & users")
print("=" * 60)

confirm = input("\nKetik 'RESET' untuk konfirmasi: ").strip()
if confirm != "RESET":
    print("Aborted.")
    sys.exit(0)

db = SessionLocal()

try:
    print("\n[1/4] Hapus board + project tree...")
    db.query(BoardCardComment).delete()
    db.query(BoardCardChecklist).delete()
    db.query(BoardCardActivity).delete()
    db.query(BoardCard).delete()
    db.query(BoardColumn).delete()
    db.query(Board).delete()
    db.query(Project).delete()

    print("[2/4] Hapus AI chat + content gen...")
    # Chat models removed from codebase
    # db.query(ChatMessage).delete()
    # db.query(ChatSummary).delete()
    # db.query(ChatConversation).delete()
    # db.query(ChatMemory).delete()
    # db.query(ChatProject).delete()
    db.query(ContentGeneration).delete()
    db.query(ContentSession).delete()
    db.query(ContentSchedule).delete()
    db.query(Document).delete()
    db.query(DocumentFolder).delete()

    print("[3/4] Hapus leads, proposals, marketing...")
    db.query(ProposalAnalytics).delete()
    db.query(ReengagementAlert).delete()
    db.query(FollowUpSequence).delete()
    db.query(ClientNote).delete()
    db.query(ClientCredential).delete()
    db.query(ClientDocument).delete()
    db.query(LeadActivityLog).delete()
    db.query(LeadAnalysis).delete()
    db.query(Proposal).delete()
    db.query(BlastCampaign).delete()
    db.query(AdsCampaign).delete()
    db.query(ScrapeHistory).delete()
    db.query(Lead).delete()
    db.query(Contact).delete()

    print("[4/4] Hapus master data + finance...")
    db.query(Subscription).delete()
    db.query(Transaction).delete()
    db.query(Wallet).delete()
    db.query(Category).delete()
    db.query(Product).delete()
    db.query(DynamicTemplate).delete()
    db.query(MessageTemplate).delete()
    db.query(ServiceItem).delete()
    db.query(AuditLog).delete()

    db.commit()
    print("\n[DONE] Database wiped. Re-seeding basic data...\n")

    # Auto re-seed basic data (categories, products, templates, wallets)
    seed_data(db)
    db.commit()

    print("\n" + "=" * 60)
    print("RESET SELESAI. Database bersih siap pakai.")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Login ke /login dengan user existing")
    print("  2. Cek /master/products, /master/categories, /master/templates → harus ada seed default")
    print("  3. Tambah data manual atau jalankan: python seed.py untuk demo data")

except Exception as e:
    db.rollback()
    print(f"\n[ERROR] {e}")
    raise
finally:
    db.close()
