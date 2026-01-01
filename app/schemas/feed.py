from pydantic import BaseModel, Field, ConfigDict, HttpUrl, field_validator
from typing import Optional, List, Union
from datetime import datetime
from uuid import UUID
from enum import Enum

# Enums matching the model
class FeedStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class FeedType(str, Enum):
    SECURITY = "security"
    EXAM_MONITORING = "exam-monitoring"
    FARM_SECURITY = "farm-security"
    STORE_MONITORING = "store-monitoring"
    HOME_SECURITY = "home-security"
    TRAFFIC_MONITORING = "traffic-monitoring"
    GENERAL = "general"

class SensitivityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

from app.schemas.contact import AlertContactResponse


# Settings Schemas
class FeedSettingsBase(BaseModel):
    push_enabled: bool = True
    email_enabled: bool = False
    sms_enabled: bool = False
    sound_enabled: bool = True
    sensitivity: Union[SensitivityLevel, str] = SensitivityLevel.MEDIUM
    auto_record: bool = True
    record_duration: int = Field(30, ge=5, le=300)  # 5s to 5min

    @field_validator('sensitivity', mode='before')
    @classmethod
    def convert_sensitivity(cls, v):
        """Convert string sensitivity to enum if needed"""
        if isinstance(v, str):
            try:
                return SensitivityLevel(v.lower())
            except ValueError:
                return SensitivityLevel.MEDIUM
        return v


class FeedSettingsCreate(FeedSettingsBase):
    pass


class FeedSettingsUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    sound_enabled: Optional[bool] = None
    sensitivity: Optional[Union[SensitivityLevel, str]] = None
    auto_record: Optional[bool] = None
    record_duration: Optional[int] = Field(None, ge=5, le=300)

    @field_validator('sensitivity', mode='before')
    @classmethod
    def convert_sensitivity(cls, v):
        """Convert string sensitivity to enum if needed"""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return SensitivityLevel(v.lower())
            except ValueError:
                return SensitivityLevel.MEDIUM
        return v


class FeedSettingsResponse(FeedSettingsBase):
    id: UUID
    feed_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Feed Schemas
class FeedBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    feed_url: str = Field(..., min_length=5, max_length=1024)
    location: str = Field(..., min_length=2, max_length=255)
    # feed_type: FeedType = FeedType.SECURITY
    feed_type: str = Field(..., min_length=2, max_length=255)
    custom_instruction: Optional[str] = None
    status: FeedStatus = FeedStatus.INACTIVE
    fps: int = Field(0, ge=0, le=60)


class FeedCreate(FeedBase):
    settings: Optional[FeedSettingsCreate] = None


class FeedUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    feed_url: Optional[str] = Field(None, min_length=5, max_length=1024)
    location: Optional[str] = Field(None, min_length=2, max_length=255)
    # feed_type: Optional[FeedType] = None
    feed_type: Optional[str] = Field(None, min_length=2, max_length=255)
    custom_instruction: Optional[str] = None
    status: Optional[FeedStatus] = None
    fps: Optional[int] = Field(None, ge=0, le=60)


class FeedResponse(FeedBase):
    id: UUID
    user_id: UUID
    fps: int
    created_at: datetime
    updated_at: datetime
    
    # Stability Metrics (Optional to handle missing DB columns)
    rolling_confidence_sum: Optional[float] = 0.0
    total_detection_count: Optional[int] = 0
    start_time: Optional[datetime] = None
    
    @property
    def stability_score(self) -> float:
        count = self.total_detection_count or 0
        if count == 0:
            return 100.0 # Default perfect stability if no data
        
        sum_val = self.rolling_confidence_sum or 0.0
        # Average confidence * 100
        return round((sum_val / count) * 100, 1)
    contacts: Optional[List[AlertContactResponse]] = []

    model_config = ConfigDict(from_attributes=True)
