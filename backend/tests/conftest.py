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
os.environ["ENABLE_BACKGROUND_SCHEDULER"] = "false"
os.environ["AUTH_ALLOWED_EMAIL_DOMAINS"] = "example.test,test.com,test.example.com,example.com"

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

# ── Savepoint support untuk pysqlite (resep resmi SQLAlchemy) ──────────────────
# Driver pysqlite secara default auto-BEGIN dan menelan SAVEPOINT, jadi kode
# P0-2 (db.begin_nested() di _generate_workflow_document) gagal dengan
# "no such savepoint" HANYA di test env. Prod MySQL tidak kena. Dengan
# isolation_level=None + event "begin" manual, SAVEPOINT jalan benar dan kode
# savepoint produksi bisa dites end-to-end (lihat test_billing_invoice_idempotency).
@event.listens_for(TEST_ENGINE, "connect")
def _sqlite_disable_autobegin(dbapi_conn, connection_record):
    dbapi_conn.isolation_level = None  # pysqlite: jangan auto-BEGIN

@event.listens_for(TEST_ENGINE, "begin")
def _sqlite_manual_begin(conn):
    # Guard: begin_nested() meng-emit SAVEPOINT lebih dulu (di SQLite itu
    # otomatis membuka transaksi). Kalau BEGIN root dicoba lagi setelahnya,
    # driver melempar "cannot start a transaction within a transaction".
    # Cek in_transaction supaya BEGIN cuma dikirim kalau benar-benar belum ada.
    dbapi_conn = conn.connection.dbapi_connection
    if not dbapi_conn.in_transaction:
        conn.exec_driver_sql("BEGIN")


def new_test_session() -> Session:
    """Create a new session bound to the test engine."""
    return sessionmaker(bind=TEST_ENGINE)()


# Patch ALL module-level engine/sessionmaker references once at module load
import models as _models_mod  # the __init__ package
from models import base as _base_mod
import main as _main_app
import app.core.dependencies as _deps_mod
from contextlib import asynccontextmanager

_orig_engine = _base_mod.engine
_orig_session_local = _base_mod.SessionLocal
_TestSessionLocal = sessionmaker(bind=TEST_ENGINE)

_base_mod.engine = TEST_ENGINE
_base_mod.SessionLocal = _TestSessionLocal
_models_mod.engine = TEST_ENGINE
_models_mod.SessionLocal = _TestSessionLocal
_main_app.engine = TEST_ENGINE
_main_app.SessionLocal = _TestSessionLocal
# dependencies.py uses: from models import SessionLocal → patches models.SessionLocal
# but it captured the binding at import time. Patch its local reference too.
_deps_mod.engine = TEST_ENGINE
_deps_mod.SessionLocal = _TestSessionLocal


@asynccontextmanager
async def _test_lifespan(app):
    """Skip production startup migration during in-memory tests."""
    yield


_main_app.app.router.lifespan_context = _test_lifespan


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
    """FastAPI TestClient bound to test DB with dependency override."""
    from fastapi.testclient import TestClient
    import models as _models
    import main as _main_app
    import app.core.dependencies as _deps
    from models import SystemSettings

    # Seed minimal system_settings needed by _get_setting calls in endpoint code
    needed_keys = {
        "admin_wa": "081234567890",
        "admin_name": "Test Admin",
        "fonnte_token": "test-fonnte-token",
        "frontend_url": "https://test.example.com",
        "app_base_url": "https://api.test.example.com",
    }
    for key, value in needed_keys.items():
        row = db_session.query(SystemSettings).filter_by(key=key).first()
        if not row:
            db_session.add(SystemSettings(key=key, value=value))
    db_session.commit()

    def _override_get_db():
        session = new_test_session()
        try:
            yield session
        finally:
            session.close()

    _main_app.app.dependency_overrides[_models.get_db] = _override_get_db
    _main_app.app.dependency_overrides[_deps.get_db] = _override_get_db
    tc = TestClient(_main_app.app)
    yield tc
    _main_app.app.dependency_overrides.clear()
