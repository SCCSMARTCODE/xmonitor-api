from typing import Any, List
from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.crud.analytics import analytics as analytics_crud
from app.crud.log import log as log_crud
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
    Get current system status for dashboard, including per-feed metrics.
    """
    # 1. Get all active feeds for user
    from app.crud.feed import feed as feed_crud
    active_feeds = await feed_crud.get_multi_by_owner(db, user_id=current_user.id, limit=100)
    
    # 2. Get latest metrics for all feeds
    latest_metrics = await analytics_crud.get_latest_metrics_by_feed(db)
    
    # Map metrics by feed_id
    metrics_map = {m.feed_id: m for m in latest_metrics if m.feed_id}
    
    feed_statuses = []
    total_cpu = 0.0
    total_memory = 0.0
    active_count = 0
    
    for feed in active_feeds:
        metric = metrics_map.get(feed.id)
        
        # Default values if no metric found
        cpu = metric.cpu_usage if metric else 0.0
        memory = metric.memory_usage if metric else 0.0
        disk = metric.disk_usage if metric else 0.0
        latency = metric.network_latency if metric else None
        
        # Calculate uptime if metric exists
        uptime = 0
        if metric:
             uptime = int((datetime.now(timezone.utc) - metric.created_at).total_seconds())
        
        total_cpu += cpu
        total_memory += memory
        active_count += 1
        
        feed_statuses.append(
            FeedSystemStatus(
                feed_id=feed.id,
                feed_name=feed.name,
                cpu_usage=cpu,
                memory_usage=memory,
                disk_usage=disk,
                uptime=uptime,
                network_latency=latency,
                status=feed.status
            )
        )
            
    # Calculate global averages/totals
    count = max(active_count, 1) # Avoid division by zero
    
    return SystemStatusResponse(
        global_cpu_usage=round(total_cpu / count, 1),
        global_memory_usage=round(total_memory / count, 1),
        total_active_feeds=len(active_feeds),
        feeds=feed_statuses
    )


@router.get("/quick-stats", response_model=QuickStatsResponse)
async def get_quick_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get quick stats for today.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    this_hour_start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    # Count calls and SMS from AlertActions
    calls_triggered = await analytics_crud.count_actions_today(db, action_type="call")
    sms_sent = await analytics_crud.count_actions_today(db, action_type="sms")
    
    # Count detections this hour
    detections_this_hour = await analytics_crud.count_detections_since(db, since=this_hour_start)
    
    # Count active alerts
    active_alerts = await analytics_crud.count_active_alerts(db)
    
    # Count events today (alerts + detections)
    events_today = await analytics_crud.count_detections_since(db, since=today_start)
    
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
        avg_cpu_usage=avg_metrics["avg_cpu_usage"],
        avg_memory_usage=avg_metrics["avg_memory_usage"],
        avg_network_latency=avg_metrics["avg_network_latency"],
        total_frames_processed=total_frames,
        total_detections=total_detections
    )


@router.get("/trends", response_model=DetectionTrendsResponse)
async def get_detection_trends(
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get detection trends over time.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Get detection types count
    detection_types = await analytics_crud.get_detection_types_count(db, since=since)
    
    # For hourly detections, we'd need to group by hour
    # For now, return empty list (would require more complex query)
    hourly_detections = []
    
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
