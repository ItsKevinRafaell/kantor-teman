"""
Image upload router — saves generated images to local storage.
Used by officekantorteman to download Imaginer COS images and store locally.
"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.core.dependencies import get_current_user, UPLOADS_DIR
from models import User

router = APIRouter(prefix="/api/images", tags=["images"])

CREATIVE_UPLOADS_DIR = os.path.join(UPLOADS_DIR, "creative")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure creative uploads directory exists
os.makedirs(CREATIVE_UPLOADS_DIR, exist_ok=True)


def _validate_image(file: UploadFile) -> None:
    """Validate uploaded file is an image and within size limits."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image, got {file.content_type}"
        )

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image format: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def _generate_filename(original_filename: str) -> str:
    """Generate unique filename preserving extension."""
    ext = os.path.splitext(original_filename)[1].lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique_id}{ext}"


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload image to local storage.

    Returns public URL: https://api.kantorteman.my.id/uploads/creative/filename.png

    Requirements:
    - Auth required (any authenticated user)
    - Image MIME type
    - Max 10MB
    """
    _validate_image(file)

    # Read file content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content)} bytes (max {MAX_FILE_SIZE})"
        )

    # Generate unique filename and save
    filename = _generate_filename(file.filename or "image.png")
    file_path = os.path.join(CREATIVE_UPLOADS_DIR, filename)

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )

    # Return public URL
    public_url = f"/uploads/creative/{filename}"

    return JSONResponse({
        "url": public_url,
        "filename": filename,
        "size": len(content),
        "content_type": file.content_type
    })
