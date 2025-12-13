import uuid
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class FeedStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class FeedType(str, enum.Enum):
    SECURITY = "security"
    EXAM_MONITORING = "exam-monitoring"
    FARM_SECURITY = "farm-security"
    STORE_MONITORING = "store-monitoring"
    HOME_SECURITY = "home-security"
    TRAFFIC_MONITORING = "traffic-monitoring"

class SensitivityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class CameraFeed(Base):
    """Camera Feed model"""
    __tablename__ = "camera_feeds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    feed_url = Column(String(1024), nullable=False)
    location = Column(String(255), nullable=False)
    feed_type = Column(String(50), default=FeedType.SECURITY.value)
    custom_instruction = Column(Text, nullable=True)
    status = Column(String(20), default=FeedStatus.INACTIVE.value)
    fps = Column(Integer, default=40)
    current_detections = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="feeds")
    settings = relationship("FeedSettings", back_populates="feed", uselist=False, cascade="all, delete-orphan")
    contacts = relationship("AlertContact", back_populates="feed", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="feed", cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="feed", cascade="all, delete-orphan")
    agent_sessions = relationship("AgentSession", back_populates="feed", cascade="all, delete-orphan")
    logs = relationship("SystemLog", back_populates="feed", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CameraFeed(id={self.id}, name='{self.name}', status='{self.status}')>"


class FeedSettings(Base):
    """Settings for a specific camera feed"""
    __tablename__ = "feed_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    feed_id = Column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), unique=True, nullable=False)
    
    # Notifications
    push_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=False)
    sms_enabled = Column(Boolean, default=False)
    sound_enabled = Column(Boolean, default=True)
    
    # Detection
    sensitivity = Column(String(20), default=SensitivityLevel.MEDIUM.value)
    auto_record = Column(Boolean, default=True)
    record_duration = Column(Integer, default=30)  # seconds
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    feed = relationship("CameraFeed", back_populates="settings")

    def __repr__(self):
        return f"<FeedSettings(feed_id={self.feed_id})>"
