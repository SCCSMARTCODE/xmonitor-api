from typing import Any, List
from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.crud.analytics import analytics as analytics_crud
from app.crud.alert import alert as alert_crud
from app.models.user import User
from app.schemas.analytics import (
    SystemStatusResponse,
    FeedSystemStatus,
    QuickStatsResponse,
    PerformanceMetricsResponse,
    DetectionTrendsResponse,
    ActivityFeedResponse,
    ActivityItem,
    TrendData,
    DetectionCreate,
    DetectionResponse,
    SystemMetricCreate,
    SystemMetricResponse
)

router = APIRouter()


@router.get("/system-status", response_model=SystemStatusResponse)
async def get_system_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current system status for dashboard - simplified to show active feeds only.
    CPU/Memory metrics removed as agents now run on server, not cameras.
    """
    # Get all feeds for user
    from app.crud.feed import feed as feed_crud
    user_feeds = await feed_crud.get_multi_by_owner(db, user_id=current_user.id, limit=100)
    
    # Get active sessions to calculate uptime
    active_sessions = await analytics_crud.get_active_agent_sessions(db)
    session_map = {session.feed_id: session for session in active_sessions}
    
    feed_statuses = []
    now = datetime.now(timezone.utc)
    
    for feed in user_feeds:
        uptime = 0
        if feed.id in session_map:
            session = session_map[feed.id]
            if session.started_at:
                # Ensure started_at is timezone aware
                started_at = session.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                uptime = int((now - started_at).total_seconds())

        # Get sensitivity from settings if available
        sensitivity = "medium"
        if feed.settings:
            sensitivity = feed.settings.sensitivity

        feed_statuses.append(
            FeedSystemStatus(
                feed_id=feed.id,
                feed_name=feed.name,
                uptime=uptime,
                network_latency=None,
                status=feed.status,
                sensitivity=sensitivity
            )
        )
    
    return SystemStatusResponse(
        total_active_feeds=len([f for f in user_feeds if f.status == 'active']),
        feeds=feed_statuses
    )


@router.get("/quick-stats", response_model=QuickStatsResponse)
async def get_quick_stats(
    db: AsyncSession = Depends(get_db),
    feed_id: UUID = Query(None),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get quick stats for today.
    """
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    this_hour_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    # Count calls and SMS from AlertActions
    calls_triggered = await analytics_crud.count_actions_today(db, action_type="call", feed_id=feed_id)
    sms_sent = await analytics_crud.count_actions_today(db, action_type="sms", feed_id=feed_id)
    
    # Count detections this hour
    detections_this_hour = await analytics_crud.count_detections_since(db, since=this_hour_start, feed_id=feed_id)
    
    # Count active alerts
    active_alerts = await analytics_crud.count_active_alerts(db, feed_id=feed_id)
    
    # Count events today (alerts + detections)
    events_today = await analytics_crud.count_detections_since(db, since=today_start, feed_id=feed_id)
    
    return QuickStatsResponse(
        events_today=events_today,
        calls_triggered=calls_triggered,
        sms_sent=sms_sent,
        detections_this_hour=detections_this_hour,
        active_alerts=active_alerts
    )


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),  # Last 1 hour to 7 days
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get system performance metrics.
    """
    # Get average metrics
    avg_metrics = await analytics_crud.get_avg_metrics(db, hours=hours)
    
    # Get total frames and detections from active sessions
    active_sessions = await analytics_crud.get_active_agent_sessions(db)
    total_frames = sum(session.frames_processed for session in active_sessions)
    total_detections = sum(session.detections_count for session in active_sessions)
    
    return PerformanceMetricsResponse(
        avg_network_latency=avg_metrics.get("avg_network_latency"),
        total_frames_processed=total_frames,
        total_detections=total_detections
    )


@router.get("/trends", response_model=DetectionTrendsResponse)
async def get_detection_trends(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
    feed_id: UUID = Query(None),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get detection confidence values over time for real-time line chart.
    Returns individual detection points with timestamp and confidence value.
    """
    from app.models.analytics import Detection
    
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Get detection types count
    detection_types = await analytics_crud.get_detection_types_count(db, since=since)
    
    # Get individual detections with timestamp and confidence
    query = (
        select(
            Detection.timestamp,
            Detection.confidence,
            Detection.detection_type
        )
        .where(Detection.timestamp >= since)
        .order_by(Detection.timestamp)
    )
    
    if feed_id:
        query = query.where(Detection.feed_id == feed_id)
    
    # Limit to last 500 points for performance
    query = query.limit(500)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Return detection confidence points
    hourly_detections = [
        TrendData(timestamp=row.timestamp, value=float(row.confidence))
        for row in rows
    ]
    
    return DetectionTrendsResponse(
        hourly_detections=hourly_detections,
        detection_types=detection_types
    )


@router.get("/activity-feed", response_model=ActivityFeedResponse)
async def get_activity_feed(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, le=100),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get live activity feed.
    """
    # Get recent alerts
    recent_alerts = await alert_crud.get_multi(db, skip=0, limit=limit // 2)
    
    # Get recent detections
    recent_detections = await analytics_crud.get_recent_detections(db, skip=0, limit=limit // 2)
    
    activities = []
    
    # Convert alerts to activities
    for alert in recent_alerts:
        activities.append(ActivityItem(
            id=alert.id,
            type="alert",
            title=alert.title,
            description=alert.description or "",
            timestamp=alert.created_at,
            severity=alert.severity,
            feed_id=alert.feed_id
        ))
    
    # Convert detections to activities
    for detection in recent_detections:
        activities.append(ActivityItem(
            id=detection.id,
            type="detection",
            title=f"{detection.detection_type.capitalize()} detected",
            description=f"Confidence: {detection.confidence:.2%}",
            timestamp=detection.timestamp,
            feed_id=detection.feed_id
        ))
    
    # Sort by timestamp descending
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    
    return ActivityFeedResponse(activities=activities[:limit])


# Detections endpoints
@router.get("/detections", response_model=List[DetectionResponse], tags=["Detections"])
async def read_detections(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    feed_id: UUID = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve recent detections.
    """
    detections = await analytics_crud.get_recent_detections(
        db, skip=skip, limit=limit, feed_id=feed_id
    )
    return detections


@router.post("/detections", response_model=DetectionResponse, status_code=status.HTTP_201_CREATED, tags=["Detections"])
async def create_detection(
    *,
    db: AsyncSession = Depends(get_db),
    detection_in: DetectionCreate,
    # Agent endpoint - could use API key authentication
) -> Any:
    """
    Create new detection (Agent endpoint).
    """
    detection = await analytics_crud.create_detection(db, obj_in=detection_in)
    return detection


# System metrics endpoint (for agent to report metrics)
@router.post("/metrics", response_model=SystemMetricResponse)
async def create_metric(
    *,
    db: AsyncSession = Depends(get_db),
    metric_in: SystemMetricCreate,
    # Agent endpoint
) -> Any:
    """
    Create new system metric (Agent endpoint).
    """
    metric = await analytics_crud.create_metric(db, obj_in=metric_in)
    return metric
