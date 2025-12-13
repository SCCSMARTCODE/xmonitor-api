from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.crud.contact import contact as contact_crud
from app.crud.feed import feed as feed_crud
from app.models.user import User
from app.schemas.contact import AlertContactCreate, AlertContactResponse

router = APIRouter()


@router.get("/feeds/{feed_id}/contacts", response_model=List[AlertContactResponse])
async def read_feed_contacts(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve all contacts for a specific feed.
    """
    # Verify feed ownership
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    contacts = await contact_crud.get_multi_by_feed(
        db, feed_id=feed_id, skip=skip, limit=limit
    )
    return contacts


@router.post("/feeds/{feed_id}/contacts", response_model=AlertContactResponse, status_code=status.HTTP_201_CREATED)
async def create_feed_contact(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    contact_in: AlertContactCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Add new contact to a feed.
    """
    # Verify feed ownership
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    contact = await contact_crud.create_with_feed(
        db, obj_in=contact_in, feed_id=feed_id
    )
    return contact


@router.delete("/feeds/{feed_id}/contacts/{contact_id}", response_model=AlertContactResponse)
async def delete_feed_contact(
    *,
    db: AsyncSession = Depends(get_db),
    feed_id: UUID,
    contact_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Remove contact from a feed.
    """
    # Verify feed ownership
    feed = await feed_crud.get(db, id=feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    if feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Verify contact exists and belongs to feed
    contact = await contact_crud.get(db, id=contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if contact.feed_id != feed_id:
        raise HTTPException(status_code=400, detail="Contact does not belong to this feed")
    
    contact = await contact_crud.remove(db, id=contact_id)
    return contact
