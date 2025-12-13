import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class AlertContact(Base):
    """Alert Contact model"""
    __tablename__ = "alert_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    feed_id = Column(UUID(as_uuid=True), ForeignKey("camera_feeds.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    feed = relationship("CameraFeed", back_populates="contacts")

    def __repr__(self):
        return f"<AlertContact(id={self.id}, name='{self.name}', feed_id={self.feed_id})>"
