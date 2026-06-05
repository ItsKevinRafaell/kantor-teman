"""Pytest fixtures for backend test suite."""
import os
import sys

# Use in-memory SQLite for all tests
os.environ["DATABASE_URL"] = "sqlite:///test_memory.db"
from cryptography.fernet import Fernet
os.environ["SECRET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests-minimum-32-bytes"  # min 32 bytes for HS256
os.environ["ENV_FILE"] = ".env.test"
os.environ["FONNTE_TOKEN"] = "test-fonnte-token"

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(base_dir)
sys.path.insert(0, base_dir)

import pytest
from fastapi.testclient import TestClient

import main as _main_app
from models import Base, engine, SessionLocal

# Create all tables once
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Database session - data persists across tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db):
    """TestClient."""
    return TestClient(_main_app.app)
