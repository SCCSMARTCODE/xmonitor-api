from typing import Dict, Set
from fastapi import WebSocket
from uuid import UUID
import json
import redis.asyncio as redis
from app.core.config import settings

class ConnectionManager:
    def __init__(self):
        # Active WebSocket connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Redis pub/sub for scaling across multiple instances
        self.redis_client: redis.Redis = None
        self.pubsub = None
    
    async def connect_redis(self):
        """Initialize Redis connection for pub/sub"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("safex_events")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket client"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket client"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to all connections of a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append((user_id, connection))
        
        # Clean up disconnected connections
        for user_id, conn in disconnected:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(conn)
    
    async def publish_event(self, event_type: str, data: dict):
        """Publish event to Redis for cross-instance broadcasting"""
        if self.redis_client:
            try:
                message = json.dumps({
                    "type": event_type,
                    "data": data
                })
                await self.redis_client.publish("safex_events", message)
            except Exception as e:
                print(f"Failed to publish to Redis: {e}")
        
        # Also broadcast locally
        await self.broadcast({
            "type": event_type,
            "data": data
        })

# Global connection manager instance
manager = ConnectionManager()
