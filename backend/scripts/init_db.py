"""Standalone DB initialization script. Run once to create all tables.

Usage:
    cd backend
    python scripts/init_db.py

Set ENV_FILE env var to choose .env file:
    ENV_FILE=.env python scripts/init_db.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.environ.get("ENV_FILE", ".env.production"))

from models import Base, engine

print(f"DB URL: {engine.url}")
Base.metadata.create_all(bind=engine)
print("All tables created successfully.")
