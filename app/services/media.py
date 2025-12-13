import os
import uuid
from typing import Optional
from pathlib import Path
from fastapi import UploadFile
import aiofiles
import cloudinary
import cloudinary.uploader
from app.core.config import settings

class MediaService:
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure Cloudinary if enabled
        if settings.cloudinary_enabled:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET
            )
    
    async def save_file_local(self, file: UploadFile, subfolder: str = "") -> tuple[str, str]:
        """
        Save file to local filesystem
        
        Returns:
            tuple: (file_path, file_url)
        """
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create subfolder if specified
        save_dir = self.upload_dir / subfolder if subfolder else self.upload_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Generate URL (relative path for serving)
        file_url = f"/media/{subfolder}/{unique_filename}" if subfolder else f"/media/{unique_filename}"
        
        return str(file_path), file_url
    
    async def upload_to_cloudinary(self, file: UploadFile, resource_type: str = "auto") -> dict:
        """
        Upload file to Cloudinary
        
        Args:
            file: File to upload
            resource_type: "image", "video", or "auto"
            
        Returns:
            dict: Cloudinary response with 'url' and 'public_id'
        """
        if not settings.cloudinary_enabled:
            raise Exception("Cloudinary is not configured")
        
        # Read file content
        content = await file.read()
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            content,
            resource_type=resource_type,
            folder="safex"
        )
        
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"]
        }
    
    async def save_media(
        self, 
        file: UploadFile, 
        media_type: str = "video",
        use_cloudinary: bool = None
    ) -> dict:
        """
        Save media file (video or image)
        
        Args:
            file: File to save
            media_type: "video" or "image"
            use_cloudinary: Override cloudinary usage (default: use if configured)
            
        Returns:
            dict: {"url": str, "storage": "local" or "cloudinary"}
        """
        # Determine storage method
        if use_cloudinary is None:
            use_cloudinary = settings.cloudinary_enabled
        
        if use_cloudinary:
            # Upload to Cloudinary
            resource_type = "video" if media_type == "video" else "image"
            result = await self.upload_to_cloudinary(file, resource_type)
            return {
                "url": result["url"],
                "storage": "cloudinary",
                "public_id": result.get("public_id")
            }
        else:
            # Save locally
            subfolder = "videos" if media_type == "video" else "images"
            file_path, file_url = await self.save_file_local(file, subfolder)
            return {
                "url": file_url,
                "storage": "local",
                "file_path": file_path
            }
    
    def get_local_file_path(self, file_url: str) -> Optional[Path]:
        """
        Get local file path from URL
        
        Args:
            file_url: URL like "/media/videos/abc123.mp4"
            
        Returns:
            Path object or None if not found
        """
        # Remove /media/ prefix
        relative_path = file_url.replace("/media/", "")
        file_path = self.upload_dir / relative_path
        
        if file_path.exists():
            return file_path
        return None

media_service = MediaService()
