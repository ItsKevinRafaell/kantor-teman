import os
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, ForeignKey, select, func, DateTime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship, joinedload, selectinload
from sqlalchemy.pool import NullPool


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leads.db")
# Auto-register PyMySQL for MySQL connections
if "mysql" in DATABASE_URL and "pymysql" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://")
_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

# Use connection pooling for better performance (except SQLite)
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


class Base(DeclarativeBase):
    pass


if os.environ.get("RUN_CREATE_ALL", "").lower() == "true":
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_audit(db: Session, actor: str, action: str, table_name: str, record_id, details=None, commit: bool = True):
    # Import here to avoid circular import at module load time
    from .lead import AuditLog
    entry = AuditLog(
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=actor,
        action=action,
        table_name=table_name,
        record_id=str(record_id),
        details=json.dumps(details) if details else None,
    )
    db.add(entry)
    # commit=False dipakai saat log dipanggil di TENGAH transaksi lain (mis. flow
    # accept proposal yang bungkus dokumen pakai SAVEPOINT/begin_nested). Commit di
    # tengah bisa batalin semantik savepoint & bikin partial state ke-commit lebih
    # awal. Caller yang set commit=False bertanggung jawab commit di akhir flow.
    if commit:
        db.commit()
    else:
        db.flush()
