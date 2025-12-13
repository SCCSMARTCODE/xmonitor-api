from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import json
from io import StringIO

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.crud.log import log as log_crud
from app.models.user import User
from app.schemas.log import (
    SystemLogCreate,
    SystemLogResponse,
    SystemLogFilter,
    LogLevel,
    LogSource
)

router = APIRouter()


@router.get("/", response_model=List[SystemLogResponse])
async def read_logs(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = Query(100, le=1000),
    source: LogSource = None,
    level: LogLevel = None,
    search: str = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve system logs with filtering.
    """
    filters = SystemLogFilter(
        source=source,
        level=level,
        search=search
    )
    
    logs = await log_crud.get_multi(
        db,
        skip=skip,
        limit=limit,
        filters=filters
    )
    return logs


@router.post("/", response_model=SystemLogResponse, status_code=status.HTTP_201_CREATED)
async def create_log(
    *,
    db: AsyncSession = Depends(get_db),
    log_in: SystemLogCreate,
    # Agent endpoint - could use API key authentication
) -> Any:
    """
    Create new log entry (Agent endpoint).
    """
    log_entry = await log_crud.create(db, obj_in=log_in)
    return log_entry


@router.post("/export")
async def export_logs(
    *,
    db: AsyncSession = Depends(get_db),
    format: str = Query("json", regex="^(json|csv)$"),
    source: LogSource = None,
    level: LogLevel = None,
    search: str = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Export logs in JSON or CSV format.
    """
    filters = SystemLogFilter(
        source=source,
        level=level,
        search=search
    )
    
    # Get all matching logs (no pagination for export)
    logs = await log_crud.get_multi(
        db,
        skip=0,
        limit=10000,  # Max export limit
        filters=filters
    )
    
    if format == "json":
        # Export as JSON
        logs_data = [
            {
                "id": str(log.id),
                "source": log.source,
                "level": log.level,
                "message": log.message,
                "details": log.details,
                "feed_id": str(log.feed_id) if log.feed_id else None,
                "user_id": str(log.user_id) if log.user_id else None,
                "alert_id": str(log.alert_id) if log.alert_id else None,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
        
        return StreamingResponse(
            iter([json.dumps(logs_data, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=logs.json"}
        )
    
    else:  # CSV format
        output = StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["id", "source", "level", "message", "details", "feed_id", "user_id", "alert_id", "created_at"]
        )
        writer.writeheader()
        
        for log in logs:
            writer.writerow({
                "id": str(log.id),
                "source": log.source,
                "level": log.level,
                "message": log.message,
                "details": log.details or "",
                "feed_id": str(log.feed_id) if log.feed_id else "",
                "user_id": str(log.user_id) if log.user_id else "",
                "alert_id": str(log.alert_id) if log.alert_id else "",
                "created_at": log.created_at.isoformat()
            })
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=logs.csv"}
        )
