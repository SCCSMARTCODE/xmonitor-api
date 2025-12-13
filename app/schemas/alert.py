from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

# Enums matching the model
class AlertStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(str, Enum):
    INTRUSION = "intrusion"
    FIRE = "fire"
    WEAPON = "weapon"
    FIGHT = "fight"
    FALL = "fall"
    CROWD = "crowd"
    OTHER = "other"


# AI Analysis Schemas
class AlertAIAnalysisBase(BaseModel):
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    detected_objects: List[str] = []
    scene_description: Optional[str] = None
    risk_factors: List[str] = []
    recommendations: List[str] = []

class AlertAIAnalysisCreate(AlertAIAnalysisBase):
    pass

class AlertAIAnalysisResponse(AlertAIAnalysisBase):
    id: UUID
    alert_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Action Schemas
class AlertActionBase(BaseModel):
    action_type: str
    recipient: str
    status: str
    details: Optional[str] = None

class AlertActionCreate(AlertActionBase):
    pass

class AlertActionResponse(AlertActionBase):
    id: UUID
    alert_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Alert Schemas
class AlertBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    status: AlertStatus = AlertStatus.ACTIVE
    severity: AlertSeverity = AlertSeverity.MEDIUM
    alert_type: AlertType = AlertType.OTHER
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

class AlertCreate(AlertBase):
    feed_id: UUID
    ai_analysis: Optional[AlertAIAnalysisCreate] = None
    actions: Optional[List[AlertActionCreate]] = None

class AlertUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[AlertStatus] = None
    severity: Optional[AlertSeverity] = None
    resolution_notes: Optional[str] = None

class AlertResolve(BaseModel):
    status: AlertStatus = AlertStatus.RESOLVED
    resolution_notes: Optional[str] = None

class AlertResponse(AlertBase):
    id: UUID
    feed_id: UUID
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None
    resolution_notes: Optional[str] = None
    
    ai_analysis: Optional[AlertAIAnalysisResponse] = None
    actions: List[AlertActionResponse] = []

    model_config = ConfigDict(from_attributes=True)
