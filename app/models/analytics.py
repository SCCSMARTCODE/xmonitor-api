import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class SystemMetric(Base):
    """System Performance Metrics"""
    __tablename__ = "system_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Metrics
    cpu_usage = Column(Float, nullable=False)  # Percentage
    memory_usage = Column(Float, nullable=False)  # Percentage
    disk_usage = Column(Float, nullable=False)  # Percentage
    network_latency = Column(Float, nullable=True)  # Milliseconds
    active_feeds = Column(Integer, default=0)
    active_agents = Column(Integer, default=0)
    
    feed_id = Column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<SystemMetric(id={self.id}, cpu={self.cpu_usage}%, mem={self.memory_usage}%)>"


class Detection(Base):
    """AI Detection Events"""
    __tablename__ = "detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    feed_id = Column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=False, index=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    
    # Detection details
    detection_type = Column(String(100), nullable=False)  # e.g., "person", "vehicle", "intrusion"
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    bounding_box = Column(JSON, nullable=True)  # {"x": 100, "y": 200, "width": 50, "height": 100}
    metadata_ = Column(JSON, nullable=True)  # Additional detection data
    
    # Frame information
    frame_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    feed = relationship("CameraFeed", back_populates="detections")
    alert = relationship("Alert", back_populates="related_detections")

    def __repr__(self):
        return f"<Detection(id={self.id}, type='{self.detection_type}', confidence={self.confidence})>"


class AgentSession(Base):
    """Agent Connection Sessions"""
    __tablename__ = "agent_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    feed_id = Column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=False, index=True)
    
    # Session details
    agent_version = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, index=True)  # "active", "disconnected", "error"
    
    # Performance stats
    frames_processed = Column(Integer, default=0)
    detections_count = Column(Integer, default=0)
    alerts_triggered = Column(Integer, default=0)
    average_latency = Column(Float, nullable=True)  # Milliseconds
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    feed = relationship("CameraFeed", back_populates="agent_sessions")

    def __repr__(self):
        return f"<AgentSession(id={self.id}, feed_id={self.feed_id}, status='{self.status}')>"
