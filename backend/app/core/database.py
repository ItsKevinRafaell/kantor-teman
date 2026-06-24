from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import DATABASE_URL

_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args=_connect_args, poolclass=NullPool)
else:
    # Shared hosting: max 6 LSAPI children, each single-threaded WSGI.
    # pool_size=20 was overkill (120 idle connections across 6 children).
    # Reduced to 2 + overflow 1 = max 18 connections total.
    # pool_recycle=300 (5min) handles aggressive MySQL wait_timeout on shared hosts.
    # pool_timeout=10 fails fast instead of hanging on connection starvation.
    engine = create_engine(
        DATABASE_URL,
        connect_args=_connect_args,
        pool_size=2,
        max_overflow=1,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_timeout=10,
    )

SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
