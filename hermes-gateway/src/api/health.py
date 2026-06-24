"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
@router.get("/api/office/health")
def health():
    return {"ok": True}
