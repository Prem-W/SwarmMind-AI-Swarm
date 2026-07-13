"""
WebSocket Endpoint for Real-Time Execution Updates

Provides live execution logs, agent status changes, and
workflow progress via WebSocket connections.
"""

import asyncio
import json
import uuid
from typing import Dict, Set

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.middleware.auth import websocket_auth
from app.services.messaging import MessageBus

logger = get_logger(__name__)
router = APIRouter(prefix="/ws")

# Active WebSocket connections
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()

        if channel not in self.connections:
            self.connections[channel] = set()
        self.connections[channel].add(websocket)

        logger.debug("WebSocket connected", channel=channel, total=len(self.connections[channel]))

    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection."""
        if channel in self.connections:
            self.connections[channel].discard(websocket)
            if not self.connections[channel]:
                del self.connections[channel]

        logger.debug("WebSocket disconnected", channel=channel)

    async def broadcast(self, channel: str, message: dict):
        """Broadcast a message to all connections in a channel."""
        if channel not in self.connections:
            return

        disconnected = set()
        for ws in self.connections[channel]:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)

        # Clean up dead connections
        for ws in disconnected:
            self.disconnect(ws, channel)

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to a specific user's connections."""
        channel = f"user:{user_id}"
        await self.broadcast(channel, message)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/execution/{execution_id}")
async def execution_websocket(websocket: WebSocket, execution_id: str):
    """
    WebSocket for real-time execution updates.
    
    Streams:
    - Execution log entries
    - Agent status changes
    - Task completions
    - Progress updates
    """
    # Authenticate
    user = await websocket_auth(websocket)
    if not user:
        await websocket.close(code=4001, reason="Authentication required")
        return

    channel = f"execution:{execution_id}"
    await manager.connect(websocket, channel)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "channel": channel,
            "execution_id": execution_id,
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        })

        # Start background task to forward Redis pub/sub messages
        forward_task = asyncio.create_task(
            _forward_execution_updates(websocket, execution_id)
        )

        # Handle client messages (commands)
        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message_type == "subscribe_agent":
                    agent_id = data.get("agent_id")
                    if agent_id:
                        await websocket.send_json({
                            "type": "subscribed",
                            "agent_id": agent_id,
                        })

                elif message_type == "command":
                    # Handle control commands (pause, resume, cancel)
                    command = data.get("command")
                    await websocket.send_json({
                        "type": "command_acknowledged",
                        "command": command,
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("WebSocket message error", error=str(e))
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected", channel=channel)
    except Exception as e:
        logger.error("WebSocket error", channel=channel, error=str(e))
    finally:
        manager.disconnect(websocket, channel)
        if "forward_task" in dir():
            forward_task.cancel()


async def _forward_execution_updates(websocket: WebSocket, execution_id: str):
    """Forward execution updates from Redis to WebSocket."""
    message_bus = MessageBus()

    try:
        async for message in message_bus.subscribe_to_agent(uuid.UUID(execution_id)):
            try:
                await websocket.send_json({
                    "type": "execution_update",
                    "data": message,
                    "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                })
            except Exception:
                break
    except Exception as e:
        logger.debug("Execution update forwarding stopped", error=str(e))


@router.websocket("/team/{team_id}")
async def team_websocket(websocket: WebSocket, team_id: str):
    """
    WebSocket for team-wide broadcasts.
    
    Streams:
    - Agent status changes
    - Workflow events
    - Team announcements
    """
    user = await websocket_auth(websocket)
    if not user:
        await websocket.close(code=4001, reason="Authentication required")
        return

    channel = f"team:{team_id}"
    await manager.connect(websocket, channel)

    try:
        await websocket.send_json({
            "type": "connection_established",
            "channel": channel,
            "team_id": team_id,
        })

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, channel)


# API endpoint to broadcast execution updates (called by orchestrator)
async def broadcast_execution_update(execution_id: uuid.UUID, event: dict):
    """Broadcast an execution update to all connected clients."""
    channel = f"execution:{str(execution_id)}"
    await manager.broadcast(channel, {
        "type": "execution_event",
        "execution_id": str(execution_id),
        "event": event,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    })
