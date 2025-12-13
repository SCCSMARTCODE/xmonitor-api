from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.services.websocket import manager
from app.core.security import verify_token
from typing import Optional

router = APIRouter()


@router.websocket("/monitoring")
async def websocket_monitoring(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time monitoring updates.
    
    Events:
    - system:status - System metrics update
    - feed:detection - New detection on a feed
    - feed:status - Feed status change
    - alert:new - New alert created
    - alert:resolved - Alert resolved
    """
    # Verify JWT token
    payload = verify_token(token, token_type="access")
    if not payload:
        await websocket.close(code=1008)  # Policy violation
        return
    
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return
    
    # Connect WebSocket
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial connection success message
        await websocket.send_json({
            "type": "connection:established",
            "data": {"user_id": user_id}
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client (e.g., subscriptions, heartbeats)
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "ping":
                # Respond to heartbeat
                await websocket.send_json({
                    "type": "pong",
                    "data": {"timestamp": data.get("timestamp")}
                })
            
            elif message_type == "subscribe":
                # Handle subscription requests (future feature)
                feed_id = data.get("feed_id")
                await websocket.send_json({
                    "type": "subscription:confirmed",
                    "data": {"feed_id": feed_id}
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


# Helper functions for sending events (can be called from other endpoints)
async def send_detection_event(feed_id: str, detection_data: dict):
    """Send detection event to all connected clients"""
    await manager.publish_event("feed:detection", {
        "feed_id": feed_id,
        **detection_data
    })


async def send_alert_event(alert_id: str, alert_data: dict):
    """Send alert event to all connected clients"""
    await manager.publish_event("alert:new", {
        "alert_id": alert_id,
        **alert_data
    })


async def send_system_status_event(status_data: dict):
    """Send system status update to all connected clients"""
    await manager.publish_event("system:status", status_data)
