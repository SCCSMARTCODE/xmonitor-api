from typing import Optional
from twilio.rest import Client
from app.core.config import settings

class NotificationService:
    def __init__(self):
        self.twilio_enabled = settings.twilio_enabled
        if self.twilio_enabled:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.from_number = settings.TWILIO_PHONE_NUMBER
    
    async def send_sms(self, to: str, message: str) -> dict:
        """
        Send SMS via Twilio
        
        Args:
            to: Phone number (E.164 format)
            message: SMS content
            
        Returns:
            dict: {"success": bool, "message_sid": str or None, "error": str or None}
        """
        if not self.twilio_enabled:
            return {
                "success": False,
                "message_sid": None,
                "error": "Twilio is not configured"
            }
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to
            )
            return {
                "success": True,
                "message_sid": message_obj.sid,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message_sid": None,
                "error": str(e)
            }
    
    async def make_call(self, to: str, twiml_url: str) -> dict:
        """
        Make a phone call via Twilio
        
        Args:
            to: Phone number (E.164 format)
            twiml_url: URL to TwiML instructions
            
        Returns:
            dict: {"success": bool, "call_sid": str or None, "error": str or None}
        """
        if not self.twilio_enabled:
            return {
                "success": False,
                "call_sid": None,
                "error": "Twilio is not configured"
            }
        
        try:
            call = self.client.calls.create(
                url=twiml_url,
                from_=self.from_number,
                to=to
            )
            return {
                "success": True,
                "call_sid": call.sid,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "call_sid": None,
                "error": str(e)
            }
    
    async def send_push_notification(self, user_id: str, title: str, body: str) -> dict:
        """
        Send push notification (placeholder for future implementation)
        
        Args:
            user_id: User ID
            title: Notification title
            body: Notification body
            
        Returns:
            dict: {"success": bool}
        """
        # TODO: Implement push notifications with Firebase/OneSignal
        return {
            "success": False,
            "error": "Push notifications not yet implemented"
        }

notification_service = NotificationService()
