"""Pytest fixtures for backend test suite — isolated in-memory DB per test."""
import os
import sys
from cryptography.fernet import Fernet

# Set env vars BEFORE any imports that read DATABASE_URL
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests-minimum-32-bytes"
os.environ["ENV_FILE"] = ".env.test"
os.environ["FONNTE_TOKEN"] = "test-fonnte-token"

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(base_dir)
sys.path.insert(0, base_dir)

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# ── In-memory test engine (shared connection for thread-safety) ────────────────
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(TEST_ENGINE, "connect")
def set_pragma(dbapi_conn, connection_record):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


def new_test_session() -> Session:
    """Create a new session bound to the test engine."""
    return sessionmaker(bind=TEST_ENGINE)()


# Patch ALL module-level engine/sessionmaker references once at module load
import models as _models_mod  # the __init__ package
from models import base as _base_mod
import main as _main_app

_orig_engine = _base_mod.engine
_orig_session_local = _base_mod.SessionLocal
_TestSessionLocal = sessionmaker(bind=TEST_ENGINE)

_base_mod.engine = TEST_ENGINE
_base_mod.SessionLocal = _TestSessionLocal
_models_mod.engine = TEST_ENGINE
_models_mod.SessionLocal = _TestSessionLocal
_main_app.engine = TEST_ENGINE
_main_app.SessionLocal = _TestSessionLocal


@pytest.fixture(scope="function", autouse=True)
def fresh_db():
    """Create fresh tables for each test, drop after. True isolation."""
    from models import Base
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def db_session(fresh_db):
    """Session per test — all changes stay within the test DB (fresh per test)."""
    session = new_test_session()
    try:
        yield session
    finally:
        session.close()


# Alias for tests that expect `db` instead of `db_session`
@pytest.fixture(scope="function")
def db(db_session):
    return db_session


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient bound to test DB."""
    from fastapi.testclient import TestClient
    import main as _main_app
    return TestClient(_main_app.app)
