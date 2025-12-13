from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.services.notifications import notification_service

router = APIRouter()


class SMSRequest(BaseModel):
    to: str
    message: str


class CallRequest(BaseModel):
    to: str
    twiml_url: str


class PushNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str


@router.post("/sms")
async def send_sms(
    *,
    request: SMSRequest,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Send SMS notification.
    """
    result = await notification_service.send_sms(request.to, request.message)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return {
        "success": True,
        "message_sid": result["message_sid"]
    }


@router.post("/call")
async def make_call(
    *,
    request: CallRequest,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Trigger phone call.
    """
    result = await notification_service.make_call(request.to, request.twiml_url)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return {
        "success": True,
        "call_sid": result["call_sid"]
    }


@router.post("/push")
async def send_push_notification(
    *,
    request: PushNotificationRequest,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Send push notification (not yet implemented).
    """
    result = await notification_service.send_push_notification(
        request.user_id,
        request.title,
        request.body
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=result.get("error", "Push notifications not yet implemented")
        )
    
    return {"success": True}
