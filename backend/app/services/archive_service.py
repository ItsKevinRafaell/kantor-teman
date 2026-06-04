"""Archive Service Layer — extracted from routers/documents.py"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import DocumentFolder, Document, Lead


# ─── Archive Folder CRUD ──────────────────────────────────────────────────────

def list_archive_folders(db: Session) -> list[dict]:
    folders = db.query(DocumentFolder).order_by(DocumentFolder.created_at).all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "parent_id": f.parent_id,
            "color": f.color,
            "created_at": f.created_at,
        }
        for f in folders
    ]


def create_archive_folder(
    db: Session,
    user_id: int,
    name: str,
    parent_id: Optional[str],
    color: str,
) -> dict:
    if parent_id and not db.query(DocumentFolder).filter(DocumentFolder.id == parent_id).first():
        raise ValueError("Parent folder tidak ditemukan")
    folder = DocumentFolder(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name.strip(),
        parent_id=parent_id or None,
        color=color or "#6B7280",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(folder)
    db.commit()
    return {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id, "color": folder.color, "created_at": folder.created_at}


def update_archive_folder(db: Session, folder_id: str, updates: dict) -> dict:
    folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first()
    if not folder:
        raise ValueError("Folder tidak ditemukan")
    if "name" in updates and updates["name"]:
        folder.name = updates["name"].strip()
    if "color" in updates and updates["color"]:
        folder.color = updates["color"]
    if "parent_id" in updates:
        parent_id = updates["parent_id"]
        if parent_id and not db.query(DocumentFolder).filter(DocumentFolder.id == parent_id).first():
            raise ValueError("Parent folder tidak ditemukan")
        if parent_creates_cycle(folder_id, parent_id, db):
            raise ValueError("Parent folder akan membuat siklus")
        folder.parent_id = parent_id or None
    db.commit()
    return {"id": folder.id, "name": folder.name, "parent_id": folder.parent_id, "color": folder.color, "created_at": folder.created_at}


def delete_archive_folder(db: Session, folder_id: str) -> None:
    folder = db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first()
    if not folder:
        raise ValueError("Folder tidak ditemukan")
    db.query(Document).filter(Document.folder_id == folder_id).update({"folder_id": None})
    db.query(DocumentFolder).filter(DocumentFolder.parent_id == folder_id).update({"parent_id": None})
    db.delete(folder)
    db.commit()


def parent_creates_cycle(folder_id: str, parent_id: Optional[str], db: Session) -> bool:
    """Detect if setting parent_id as parent of folder_id would create a cycle."""
    seen = set()
    current_id = parent_id
    while current_id:
        if current_id == folder_id or current_id in seen:
            return True
        seen.add(current_id)
        current = db.query(DocumentFolder).filter(DocumentFolder.id == current_id).first()
        current_id = current.parent_id if current else None
    return False


# ─── Archive Document CRUD ────────────────────────────────────────────────────

def _archive_doc_to_dict(doc: Document) -> dict:
    try:
        tags = json.loads(doc.tags) if doc.tags else []
    except Exception:
        tags = []
    return {
        "id": doc.id,
        "folder_id": doc.folder_id,
        "title": doc.title,
        "body": doc.body,
        "url": doc.url,
        "tags": tags,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


def list_archive_docs(
    db: Session,
    user_id: int,
    folder_id: Optional[str],
    search: Optional[str],
    limit: int = 50,
    unfoldered: Optional[bool] = None,
) -> list[dict]:
    q = db.query(Document)
    if unfoldered:
        q = q.filter(Document.folder_id == None)
    elif folder_id is not None:
        q = q.filter(Document.folder_id == folder_id)
    if search:
        q = q.filter(Document.title.ilike(f"%{search}%"))
    docs = q.order_by(Document.updated_at.desc(), Document.created_at.desc()).limit(limit).all()
    return [_archive_doc_to_dict(d) for d in docs]


def get_archive_doc(db: Session, doc_id: str) -> dict:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise ValueError("Dokumen tidak ditemukan")
    return _archive_doc_to_dict(doc)


def create_archive_doc(
    db: Session,
    user_id: int,
    title: str,
    body: Optional[str],
    url: Optional[str],
    tags: Optional[list],
    folder_id: Optional[str],
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    if folder_id and not db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first():
        raise ValueError("Folder tidak ditemukan")
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=user_id,
        folder_id=folder_id or None,
        title=title.strip(),
        body=body or None,
        url=url or None,
        tags=json.dumps(tags or []),
        created_at=now,
        updated_at=now,
    )
    db.add(doc)
    db.commit()
    return _archive_doc_to_dict(doc)


def update_archive_doc(db: Session, doc_id: str, updates: dict) -> dict:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise ValueError("Dokumen tidak ditemukan")
    if "title" in updates and updates["title"]:
        doc.title = updates["title"].strip()
    if "body" in updates:
        doc.body = updates["body"] or None
    if "url" in updates:
        doc.url = updates["url"] or None
    if "tags" in updates:
        doc.tags = json.dumps(updates["tags"] or [])
    if "folder_id" in updates:
        folder_id = updates["folder_id"]
        if folder_id and not db.query(DocumentFolder).filter(DocumentFolder.id == folder_id).first():
            raise ValueError("Folder tidak ditemukan")
        doc.folder_id = folder_id or None
    doc.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return _archive_doc_to_dict(doc)


def delete_archive_doc(db: Session, doc_id: str) -> None:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise ValueError("Dokumen tidak ditemukan")
    db.delete(doc)
    db.commit()