import uuid
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum, Text, DateTime, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"

class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(str, enum.Enum):
    INTRUSION = "intrusion"
    FIRE = "fire"
    WEAPON = "weapon"
    FIGHT = "fight"
    FALL = "fall"
    CROWD = "crowd"
    OTHER = "other"

class Alert(Base):
    """Alert model"""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    feed_id = Column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=AlertStatus.ACTIVE.value, index=True)
    severity = Column(String(20), default=AlertSeverity.MEDIUM.value, index=True)
    alert_type = Column(String(50), default=AlertType.OTHER.value)
    
    # Media evidence
    video_url = Column(String(1024), nullable=True)
    thumbnail_url = Column(String(1024), nullable=True)
    
    # Resolution details
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    feed = relationship("CameraFeed", back_populates="alerts")
    resolver = relationship("User", backref="resolved_alerts")
    ai_analysis = relationship("AlertAIAnalysis", back_populates="alert", uselist=False, cascade="all, delete-orphan")
    actions = relationship("AlertAction", back_populates="alert", cascade="all, delete-orphan")
    related_detections = relationship("Detection", back_populates="alert", cascade="all, delete-orphan")
    logs = relationship("SystemLog", back_populates="alert", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Alert(id={self.id}, title='{self.title}', severity='{self.severity}')>"


class AlertAIAnalysis(Base):
    """AI Analysis details for an alert"""
    __tablename__ = "alert_ai_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), unique=True, nullable=False)
    
    confidence_score = Column(Float, nullable=False)
    detected_objects = Column(JSON, default=list)  # List of objects detected
    scene_description = Column(Text, nullable=True)
    risk_factors = Column(JSON, default=list)  # List of risk factors identified
    recommendations = Column(JSON, default=list)  # List of recommended actions
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    alert = relationship("Alert", back_populates="ai_analysis")

    def __repr__(self):
        return f"<AlertAIAnalysis(alert_id={self.alert_id}, confidence={self.confidence_score})>"


class AlertAction(Base):
    """Actions taken for an alert (e.g., SMS sent)"""
    __tablename__ = "alert_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False)
    
    action_type = Column(String(50), nullable=False)  # sms, call, email, push
    recipient = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False)  # pending, sent, failed
    details = Column(Text, nullable=True)  # Error message or provider ID
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    alert = relationship("Alert", back_populates="actions")

    def __repr__(self):
        return f"<AlertAction(id={self.id}, type='{self.action_type}', status='{self.status}')>"
