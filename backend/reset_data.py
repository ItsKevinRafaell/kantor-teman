"""
Reset script: Hapus semua data dev/test, pertahankan data bisnis yang di-seed.

PERTAHANKAN:
  - users, system_settings, provider_configs
  - categories, products, dynamic_templates
  - wallets, transactions, subscriptions
  - leads WHERE status = 'Closed/Client'  (PT MLS, PT MHK)
  - projects linked ke client leads

HAPUS:
  - boards, board_columns, board_cards, board_card_comments/checklists/activities
  - chat_projects, chat_conversations, chat_messages, chat_memories, chat_summaries
  - content_generations, content_sessions, content_schedules
  - documents, document_folders
  - reengagement_alerts, followup_sequences
  - client_notes, client_credentials, client_documents
  - lead_activity_logs, lead_analyses
  - proposals
  - blast_campaigns, ads_campaigns
  - scrape_history
  - leads WHERE status != 'Closed/Client'
  - contacts
  - audit_logs
  - message_templates
  - service_items

Jalankan: python reset_data.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from main import (
    SessionLocal,
    Lead, Contact, Proposal, ScrapeHistory, LeadActivityLog, LeadAnalysis,
    Project, Board, BoardColumn, BoardCard, BoardCardComment, BoardCardChecklist, BoardCardActivity,
    BlastCampaign, FollowUpSequence, ReengagementAlert, AdsCampaign,
    ChatProject, ChatConversation, ChatMessage, ChatMemory, ChatSummary,
    ContentSession, ContentGeneration, ContentSchedule,
    Document, DocumentFolder,
    ClientNote, ClientCredential, ClientDocument,
    MessageTemplate, ServiceItem, AuditLog,
)

db = SessionLocal()

try:
    print("Starting reset...")

    # --- Board (board_card_* first, then cards → columns → boards) ---
    deleted = db.query(BoardCardComment).delete()
    print(f"  Deleted {deleted} board_card_comments")
    deleted = db.query(BoardCardChecklist).delete()
    print(f"  Deleted {deleted} board_card_checklists")
    deleted = db.query(BoardCardActivity).delete()
    print(f"  Deleted {deleted} board_card_activities")
    deleted = db.query(BoardCard).delete()
    print(f"  Deleted {deleted} board_cards")
    deleted = db.query(BoardColumn).delete()
    print(f"  Deleted {deleted} board_columns")
    deleted = db.query(Board).delete()
    print(f"  Deleted {deleted} boards")

    # --- AI Chat ---
    deleted = db.query(ChatMessage).delete()
    print(f"  Deleted {deleted} chat_messages")
    deleted = db.query(ChatSummary).delete()
    print(f"  Deleted {deleted} chat_summaries")
    deleted = db.query(ChatConversation).delete()
    print(f"  Deleted {deleted} chat_conversations")
    deleted = db.query(ChatMemory).delete()
    print(f"  Deleted {deleted} chat_memories")
    deleted = db.query(ChatProject).delete()
    print(f"  Deleted {deleted} chat_projects")

    # --- Content Generator ---
    deleted = db.query(ContentGeneration).delete()
    print(f"  Deleted {deleted} content_generations")
    deleted = db.query(ContentSession).delete()
    print(f"  Deleted {deleted} content_sessions")
    deleted = db.query(ContentSchedule).delete()
    print(f"  Deleted {deleted} content_schedules")

    # --- Documents ---
    deleted = db.query(Document).delete()
    print(f"  Deleted {deleted} documents")
    deleted = db.query(DocumentFolder).delete()
    print(f"  Deleted {deleted} document_folders")

    # --- Lead-dependent tables ---
    deleted = db.query(ReengagementAlert).delete()
    print(f"  Deleted {deleted} reengagement_alerts")
    deleted = db.query(FollowUpSequence).delete()
    print(f"  Deleted {deleted} followup_sequences")
    deleted = db.query(ClientNote).delete()
    print(f"  Deleted {deleted} client_notes")
    deleted = db.query(ClientCredential).delete()
    print(f"  Deleted {deleted} client_credentials")
    deleted = db.query(ClientDocument).delete()
    print(f"  Deleted {deleted} client_documents")
    deleted = db.query(LeadActivityLog).delete()
    print(f"  Deleted {deleted} lead_activity_logs")
    deleted = db.query(LeadAnalysis).delete()
    print(f"  Deleted {deleted} lead_analyses")
    deleted = db.query(Proposal).delete()
    print(f"  Deleted {deleted} proposals")

    # --- Marketing ---
    deleted = db.query(BlastCampaign).delete()
    print(f"  Deleted {deleted} blast_campaigns")
    deleted = db.query(AdsCampaign).delete()
    print(f"  Deleted {deleted} ads_campaigns")

    # --- Scraping ---
    deleted = db.query(ScrapeHistory).delete()
    print(f"  Deleted {deleted} scrape_history")

    # --- Leads (keep Closed/Client only) ---
    client_ids = {l.id for l in db.query(Lead).filter(Lead.status == "Closed/Client").all()}
    deleted = db.query(Lead).filter(Lead.status != "Closed/Client").delete(synchronize_session=False)
    print(f"  Deleted {deleted} scraped/test leads (kept {len(client_ids)} clients)")

    # --- Contacts ---
    deleted = db.query(Contact).delete()
    print(f"  Deleted {deleted} contacts")

    # --- Misc ---
    deleted = db.query(AuditLog).delete()
    print(f"  Deleted {deleted} audit_logs")
    deleted = db.query(MessageTemplate).delete()
    print(f"  Deleted {deleted} message_templates")
    deleted = db.query(ServiceItem).delete()
    print(f"  Deleted {deleted} service_items")

    db.commit()
    print("\nReset selesai! Database siap production.")

except Exception as e:
    db.rollback()
    print(f"\nERROR: {e}")
    raise
finally:
    db.close()
