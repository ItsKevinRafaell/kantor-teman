"""Pytest fixtures for backend test suite."""
import os
import sys

# Use in-memory SQLite for all tests
os.environ["DATABASE_URL"] = "sqlite:///test_memory.db"
from cryptography.fernet import Fernet
os.environ["SECRET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests!"
os.environ["ENV_FILE"] = ".env.test"
os.environ["FONNTE_TOKEN"] = "test-fonnte-token"

# Set working directory
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

# Create tables before tests
import main as _main_module
from models import Base, engine, SessionLocal, User, Wallet, Lead, Subscription, Transaction
from app.core.dependencies import hash_password


@pytest.fixture(scope="function")
def db():
    """Create fresh DB for each test."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """TestClient with fresh DB."""
    Base.metadata.create_all(bind=engine)
    # Import app after env vars are set
    import importlib
    import main as _main
    importlib.reload(_main)
    return TestClient(_main.app)


@pytest.fixture(scope="function")
def admin_user(db):
    """Admin user for auth tests."""
    user = User(
        name="Admin Test",
        email="admin@test.com",
        hashed_password=hash_password("admin123"),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def regular_user(db):
    """Regular user for auth tests."""
    user = User(
        name="Regular Test",
        email="user@test.com",
        hashed_password=hash_password("user123"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_token(admin_user):
    """JWT token for admin user."""
    from app.core.dependencies import create_token
    return create_token(admin_user.id, admin_user.email)


@pytest.fixture(scope="function")
def regular_token(regular_user):
    """JWT token for regular user."""
    from app.core.dependencies import create_token
    return create_token(regular_user.id, regular_user.email)
