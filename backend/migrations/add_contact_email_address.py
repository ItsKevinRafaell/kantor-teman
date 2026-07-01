"""Migration: Add email and address columns to contacts table

Run with: python migrations/add_contact_email_address.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SessionLocal, Base, engine
from sqlalchemy import inspect, text

def migrate():
    db = SessionLocal()
    conn = engine.connect()
    try:
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("contacts")]

        if "email" not in columns:
            print("Adding email column to contacts...")
            conn.execute(text("ALTER TABLE contacts ADD COLUMN email VARCHAR(255)"))
            print("  Done: email added")
        else:
            print("  Skip: email already exists")

        if "address" not in columns:
            print("Adding address column to contacts...")
            conn.execute(text("ALTER TABLE contacts ADD COLUMN address VARCHAR(500)"))
            print("  Done: address added")
        else:
            print("  Skip: address already exists")

        conn.commit()
        print("\nMigration complete!")
    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed: {e}")
        raise
    finally:
        conn.close()
        db.close()

if __name__ == "__main__":
    migrate()
