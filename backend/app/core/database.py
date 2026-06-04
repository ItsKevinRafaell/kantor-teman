from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import DATABASE_URL

_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args=_connect_args, poolclass=NullPool)
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args=_connect_args,
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

SessionLocal = sessionmaker(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
