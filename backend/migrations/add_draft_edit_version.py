"""Migration: Add document drafts, versions, and editable columns

Run with: python migrations/add_draft_edit_version.py
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
        tables = inspector.get_table_names()

        # 1. Create document_drafts table
        if "document_drafts" not in tables:
            print("Creating document_drafts table...")
            conn.execute(text("""
                CREATE TABLE document_drafts (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    template_id VARCHAR(36),
                    template_name VARCHAR(255),
                    target_type VARCHAR(50),
                    target_id VARCHAR(255),
                    variables_json TEXT NOT NULL,
                    line_items_json TEXT,
                    created_at VARCHAR(255) NOT NULL,
                    updated_at VARCHAR(255)
                )
            """))
            print("  Done: document_drafts created")
        else:
            print("  Skip: document_drafts already exists")

        # 2. Create document_versions table
        if "document_versions" not in tables:
            print("Creating document_versions table...")
            conn.execute(text("""
                CREATE TABLE document_versions (
                    id VARCHAR(36) PRIMARY KEY,
                    document_id VARCHAR(36) NOT NULL,
                    version_number INTEGER NOT NULL,
                    variables_json TEXT,
                    html_content TEXT,
                    change_summary VARCHAR(500),
                    created_at VARCHAR(255) NOT NULL,
                    created_by VARCHAR(255)
                )
            """))
            print("  Done: document_versions created")
        else:
            print("  Skip: document_versions already exists")

        # 3. Add edited_html + is_edited columns to generated_documents
        columns = [c["name"] for c in inspector.get_columns("generated_documents")]
        if "edited_html" not in columns:
            print("Adding edited_html column to generated_documents...")
            conn.execute(text("ALTER TABLE generated_documents ADD COLUMN edited_html TEXT"))
            print("  Done: edited_html added")
        else:
            print("  Skip: edited_html already exists")

        if "is_edited" not in columns:
            print("Adding is_edited column to generated_documents...")
            # SQLite uses INTEGER for boolean, MySQL uses TINYINT(1)
            conn.execute(text("ALTER TABLE generated_documents ADD COLUMN is_edited BOOLEAN DEFAULT FALSE"))
            print("  Done: is_edited added")
        else:
            print("  Skip: is_edited already exists")

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
