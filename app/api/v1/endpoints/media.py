from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.media import media_service

router = APIRouter()


@router.post("/upload")
async def upload_media(
    *,
    file: UploadFile = File(...),
    media_type: str = "video",  # "video" or "image"
    use_cloudinary: bool = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Upload media file (video or snapshot).
    """
    # Validate file size
    from app.core.config import settings
    
    # Validate media type
    if media_type not in ["video", "image"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="media_type must be 'video' or 'image'"
        )
    
    # Validate file extension
    allowed_video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    allowed_image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    
    file_extension = file.filename.split(".")[-1].lower() if file.filename else ""
    
    if media_type == "video" and f".{file_extension}" not in allowed_video_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid video file type. Allowed: {', '.join(allowed_video_extensions)}"
        )
    
    if media_type == "image" and f".{file_extension}" not in allowed_image_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file type. Allowed: {', '.join(allowed_image_extensions)}"
        )
    
    try:
        result = await media_service.save_media(file, media_type, use_cloudinary)
        return {
            "success": True,
            "url": result["url"],
            "storage": result["storage"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/{file_path:path}")
async def get_media(file_path: str):
    """
    Retrieve media file from local storage.
    Note: Cloudinary files are served directly from Cloudinary URLs.
    """
    # Construct URL format
    file_url = f"/media/{file_path}"
    
    local_file_path = media_service.get_local_file_path(file_url)
    
    if not local_file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found"
        )
    
    return FileResponse(local_file_path)
