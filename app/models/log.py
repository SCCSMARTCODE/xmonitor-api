import uuid
from sqlalchemy import Column, String, ForeignKey, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogSource(str, enum.Enum):
    API = "api"
    AGENT = "agent"
    SYSTEM = "system"
    USER = "user"

class SystemLog(Base):
    """System Log model"""
    __tablename__ = "system_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Source information
    source = Column(String(50), default=LogSource.SYSTEM.value, index=True)
    level = Column(String(20), default=LogLevel.INFO.value, index=True)
    
    # Optional associations
    feed_id = Column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    
    # Log content
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # Additional context or stack trace
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    feed = relationship("CameraFeed", back_populates="logs")
    user = relationship("User", backref="logs")
    alert = relationship("Alert", back_populates="logs")

    # Composite indexes
    __table_args__ = (
        Index('ix_logs_source_level', 'source', 'level'),
        Index('ix_logs_created_source', 'created_at', 'source'),
    )

    def __repr__(self):
        return f"<SystemLog(id={self.id}, level='{self.level}', source='{self.source}')>"

