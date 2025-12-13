from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, feeds, contacts, alerts, logs, analytics, media, notifications

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(feeds.router, prefix="/feeds", tags=["Camera Feeds"])
api_router.include_router(contacts.router, tags=["Alert Contacts"])  # No prefix as paths start with /feeds
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(logs.router, prefix="/logs", tags=["System Logs"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# Note: WebSocket route is added directly in main.py







