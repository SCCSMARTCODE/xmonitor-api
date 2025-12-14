# Models package
# Import all models to ensure SQLAlchemy relationships are properly configured
from app.models.user import User
from app.models.feed import CameraFeed, FeedSettings
from app.models.contact import AlertContact
from app.models.alert import Alert, AlertAIAnalysis, AlertAction
from app.models.analytics import SystemMetric, Detection, AgentSession
from app.models.log import SystemLog

__all__ = [
    "User",
    "CameraFeed",
    "FeedSettings",
    "AlertContact",
    "Alert",
    "AlertAIAnalysis",
    "AlertAction",
    "Detection",
    "AgentSession",
    "SystemMetric",
    "SystemLog",
]
