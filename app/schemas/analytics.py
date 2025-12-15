from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# System Metrics
class SystemMetricBase(BaseModel):
    network_latency: Optional[float] = None
    active_feeds: int = 0
    active_agents: int = 0
    feed_id: Optional[UUID] = None

class SystemMetricCreate(SystemMetricBase):
    pass

class SystemMetricResponse(SystemMetricBase):
    id: UUID
    created_at: datetime
    feed_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


# Detections
class DetectionBase(BaseModel):
    detection_type: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: Optional[str] = None
    risk_level: Optional[str] = None
    context_tags: Optional[List[str]] = None
    bounding_box: Optional[Dict[str, Any]] = None
    frame_id: Optional[str] = None

class DetectionCreate(DetectionBase):
    feed_id: UUID
    alert_id: Optional[UUID] = None

class DetectionResponse(DetectionBase):
    id: UUID
    feed_id: UUID
    alert_id: Optional[UUID] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Agent Sessions
class AgentSessionBase(BaseModel):
    agent_version: Optional[str] = None
    status: str = "active"
    frames_processed: int = 0
    detections_count: int = 0
    alerts_triggered: int = 0
    average_latency: Optional[float] = None

class AgentSessionCreate(AgentSessionBase):
    feed_id: UUID

class AgentSessionUpdate(BaseModel):
    status: Optional[str] = None
    frames_processed: Optional[int] = None
    detections_count: Optional[int] = None
    alerts_triggered: Optional[int] = None
    average_latency: Optional[float] = None

class AgentSessionResponse(AgentSessionBase):
    id: UUID
    feed_id: UUID
    started_at: datetime
    last_heartbeat: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Analytics Aggregated Responses
class FeedSystemStatus(BaseModel):
    """System status for a specific feed"""
    feed_id: UUID
    feed_name: str
    uptime: int
    network_latency: Optional[float] = None
    status: str = "active"
    sensitivity: Optional[str] = "medium"

class SystemStatusResponse(BaseModel):
    """Current system status for dashboard"""
    total_active_feeds: int
    feeds: List[FeedSystemStatus]

class QuickStatsResponse(BaseModel):
    """Quick stats for today"""
    events_today: int
    calls_triggered: int
    sms_sent: int
    detections_this_hour: int
    active_alerts: int

class PerformanceMetricsResponse(BaseModel):
    """System performance metrics"""
    avg_network_latency: Optional[float] = None
    total_frames_processed: int
    total_detections: int

class TrendData(BaseModel):
    """Data point for trend charts"""
    timestamp: datetime
    value: float

class DetectionTrendsResponse(BaseModel):
    """Detection trends over time"""
    hourly_detections: List[TrendData]
    detection_types: Dict[str, int]  # {"person": 50, "vehicle": 30}

class ActivityItem(BaseModel):
    """Live activity feed item"""
    id: UUID
    type: str  # "detection", "alert", "log"
    title: str
    description: str
    timestamp: datetime
    severity: Optional[str] = None
    feed_id: Optional[UUID] = None

class ActivityFeedResponse(BaseModel):
    """Live activity feed"""
    activities: List[ActivityItem]
