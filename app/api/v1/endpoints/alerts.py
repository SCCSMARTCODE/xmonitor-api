from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, verify_agent_api_key
from app.crud.alert import alert as alert_crud
from app.crud.feed import feed as feed_crud
from app.models.user import User
from app.schemas.alert import (
    AlertCreate,
    AlertResponse,
    AlertResolve,
    AlertStatus,
    AlertSeverity
)

router = APIRouter()


@router.get("/", response_model=List[AlertResponse])
async def read_alerts(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    feed_id: Optional[UUID] = None,
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve alerts with filtering.
    """
    # If feed_id is provided, verify ownership
    if feed_id:
        feed = await feed_crud.get(db, id=feed_id)
        if not feed:
            raise HTTPException(status_code=404, detail="Feed not found")
        if feed.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
    # TODO: If no feed_id, we should filter by all feeds owned by user
    # For now, we'll return all alerts (assuming single user or admin view for demo)
    # In production, we must filter by user's feeds
    
    alerts = await alert_crud.get_multi(
        db,
        skip=skip,
        limit=limit,
        feed_id=feed_id,
        status=status.value if status else None,
        severity=severity.value if severity else None
    )
    
    # Filter alerts belonging to user's feeds
    # This is inefficient, better to do in SQL join, but works for MVP
    user_alerts = []
    for alert in alerts:
        feed = await feed_crud.get(db, id=alert.feed_id)
        if feed and feed.user_id == current_user.id:
            user_alerts.append(alert)
            
    return user_alerts


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    *,
    db: AsyncSession = Depends(get_db),
    alert_in: AlertCreate,
    # This endpoint is primarily for the Agent, so we might use API Key auth
    # For now, we'll allow authenticated users (like the agent with a token)
    # or we can add a dependency for Agent API Key
) -> Any:
    """
    Create new alert (Agent endpoint).
    """
    # Verify feed exists
    feed = await feed_crud.get(db, id=alert_in.feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    alert = await alert_crud.create(db, obj_in=alert_in)
    return alert


@router.get("/{alert_id}", response_model=AlertResponse)
async def read_alert(
    *,
    db: AsyncSession = Depends(get_db),
    alert_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get alert details.
    """
    alert = await alert_crud.get(db, id=alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Verify ownership via feed
    feed = await feed_crud.get(db, id=alert.feed_id)
    if not feed or feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    *,
    db: AsyncSession = Depends(get_db),
    alert_id: UUID,
    resolve_in: AlertResolve,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Resolve an alert.
    """
    alert = await alert_crud.get(db, id=alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Verify ownership
    feed = await feed_crud.get(db, id=alert.feed_id)
    if not feed or feed.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    alert = await alert_crud.resolve(
        db, db_obj=alert, obj_in=resolve_in, user_id=current_user.id
    )
    return alert
