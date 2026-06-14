"""Migration: Add lead_id to contacts, provider to ai_proxies

Run with: python migrations/add_lead_id_and_provider.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SessionLocal, Contact, Lead, AIProxy

def normalize_phone(phone: str) -> str:
    """Normalize phone to 08xx format."""
    if not phone:
        return ""
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('62'):
        digits = '0' + digits[2:]
    elif digits.startswith('+62'):
        digits = '0' + digits[3:]
    return digits

def migrate():
    db = SessionLocal()
    try:
        # 1. Add lead_id to contacts (backfill by phone match)
        print("Migrating contacts.lead_id...")
        contacts = db.query(Contact).filter(Contact.lead_id == None).all()
        for contact in contacts:
            if not contact.phone_number:
                continue
            normalized = normalize_phone(contact.phone_number)
            lead = db.query(Lead).filter(Lead.phone_number == normalized).first()
            if lead:
                contact.lead_id = lead.id
                print(f"  Linked contact {contact.id} -> lead {lead.id}")
            else:
                print(f"  No lead found for contact {contact.id} (phone: {normalized})")
        db.commit()
        print(f"  Done: {len(contacts)} contacts processed")

        # 2. Normalize provider to 9router
        print("Migrating ai_proxies.provider...")
        proxies = db.query(AIProxy).filter(
            (AIProxy.provider == None) | (AIProxy.provider == "") | (AIProxy.provider != "9router")
        ).all()
        for proxy in proxies:
            proxy.provider = "9router"
            print(f"  Set provider=9router for AIProxy {proxy.id}")
        db.commit()
        print(f"  Done: {len(proxies)} proxies updated")

        print("\nMigration complete!")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
