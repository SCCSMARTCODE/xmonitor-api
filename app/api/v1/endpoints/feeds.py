from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_agent_api_key
from app.crud.feed import feed as feed_crud
from app.models.user import User
from app.models.feed import FeedStatus
from app.schemas.feed import (
    FeedCreate,
    FeedUpdate,
    FeedResponse,
    FeedSettingsUpdate,
    FeedSettingsResponse
)

router = APIRouter()


@router.get("/", response_model=List[FeedResponse])
async def read_feeds(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve all feeds for current user.
    """
    feeds = await feed_crud.get_multi_by_owner(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return feeds


@router.get("/active", response_model=List[FeedResponse])
async def read_active_feeds(
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_agent_api_key),
) -> Any:
    """
    Get all active feeds (Agent endpoint).
    Requires X-API-Key.
    """
    feeds = await feed_crud.get_all_active(db)
    return feeds


@router.post("/", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(
    *,
    db: AsyncSession = Depends(get_db),
    feed_in: FeedCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create new camera feed.
    """
    feed = await feed_crud.create_with_owner(
        db, obj_in=feed_in, user_id=current_user.id
    )
    return feed


@router.get("/{feed_id}", response_model=FeedResponse)
async def read_feed(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get feed details by ID.
    """
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return feed


@router.patch("/{feed_id}", response_model=FeedResponse)
async def update_feed(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    feed_in: FeedUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update feed details.
    """
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    feed = await feed_crud.update(db, db_obj=feed, obj_in=feed_in)
    return feed


@router.delete("/{feed_id}", response_model=FeedResponse)
async def delete_feed(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete feed.
    """
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    feed = await feed_crud.remove(db, id=feed_id)
    return feed


@router.post("/{feed_id}/toggle", response_model=FeedResponse)
async def toggle_feed_status(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Toggle feed status (active/inactive).
    """
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    new_status = FeedStatus.ACTIVE if feed.status == FeedStatus.INACTIVE.value else FeedStatus.INACTIVE
    
    update_data = {"status": new_status}
    if new_status == FeedStatus.ACTIVE:
        from datetime import datetime
        update_data["start_time"] = datetime.now()
    else:
        update_data["start_time"] = None
        
    feed = await feed_crud.update(db, db_obj=feed, obj_in=update_data)
    
    # Trigger Background Worker if ACTIVE
    if new_status == FeedStatus.ACTIVE:
        from app.worker.tasks import monitor_feed_task
        monitor_feed_task.delay(str(feed.id))

    return feed


@router.get("/{feed_id}/settings", response_model=FeedSettingsResponse)
async def read_feed_settings(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get feed settings.
    """
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return feed.settings


@router.patch("/{feed_id}/settings", response_model=FeedSettingsResponse)
async def update_feed_settings(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    settings_in: FeedSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update feed settings.
    """
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    settings = await feed_crud.update_settings(db, feed_id=feed_id, obj_in=settings_in)
    return settings
