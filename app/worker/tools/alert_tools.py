"""
LangChain tools for alert and response actions
"""
import logging
import os
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import json
from twilio.rest import Client

from langchain.tools import tool
import requests

logger = logging.getLogger(__name__)


# Global config reference (set by get_alert_tools)
_CONFIG: Dict[str, Any] = {}



class SMSInput(BaseModel):
    phone_number: str = Field(..., description="Recipient phone number in E.164 format")
    message: str = Field(..., description="Message content to send via SMS")


class CallInput(BaseModel):
    phone_number: str = Field(..., description="Recipient phone number in E.164 format")
    call_message: str = Field(..., description="Message content to deliver during the call")

@tool(args_schema=SMSInput)
def send_sms(phone_number: str, message: str) -> str:
    """
    This tool sends an SMS alert to the specified phone number.
    USE ONLY when you need to send an SMS alert.
    """
    try:
        # if not _CONFIG.get('alerts', {}).get('enable_sms', False):
        #     return "SMS alerts are disabled in configuration"

        logger.critical(f"SMS SENT to {phone_number}: {message}")

        client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        twilio_sms = client.messages.create(
            messaging_service_sid=os.getenv("TWILIO_MESSAGING_SERVICE_SID"),
            body=message,
            to=phone_number
        )

        print("SMS SID:", twilio_sms.sid)

        return f"SMS sent to {phone_number}"

    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return f"Error sending SMS: {str(e)}"


# @tool(args_schema=CallInput)
# def outbound_call(phone_number: str, call_message) -> str:
#     """
#     Initiate an emergency call or notification.
#     USE ONLY for critical, life-threatening situations.
#     #
#     Args:
#         contact: Emergency contact identifier
#         reason: Reason for emergency call
#     #
#     Returns:
#         Confirmation message
#     """
#     try:
#         pass
#     except Exception as e:
#         logger.error(f"Error initiating emergency call: {str(e)}")
#         return f"Error initiating emergency call: {str(e)}"


def get_alert_tools(config: Dict[str, Any]) -> List:
    """
    Get configured LangChain tools for the agent

    Args:
        config: Application configuration

    Returns:
        List of LangChain tools
    """
    global _CONFIG
    _CONFIG = config

    return [
        # send_alert,
        send_sms,
        # emergency_call,
        # query_xmonitor_api
    ]
