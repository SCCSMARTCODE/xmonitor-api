from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

# Enums matching the model
class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogSource(str, Enum):
    API = "api"
    AGENT = "agent"
    SYSTEM = "system"
    USER = "user"

class SystemLogBase(BaseModel):
    source: LogSource = LogSource.SYSTEM
    level: LogLevel = LogLevel.INFO
    feed_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    alert_id: Optional[UUID] = None
    message: str = Field(..., min_length=1)
    details: Optional[str] = None

class SystemLogCreate(SystemLogBase):
    pass

class SystemLogResponse(SystemLogBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SystemLogFilter(BaseModel):
    """Filter parameters for log queries"""
    source: Optional[LogSource] = None
    level: Optional[LogLevel] = None
    feed_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    alert_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None  # Search in message field

class LogExportRequest(BaseModel):
    """Request parameters for log export"""
    format: str = Field("json", pattern="^(json|csv)$")
    filters: Optional[SystemLogFilter] = None
