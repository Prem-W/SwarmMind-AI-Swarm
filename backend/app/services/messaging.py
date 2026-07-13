"""
Agent Messaging Service

Provides agent-to-agent communication via Redis pub/sub.
Supports direct messages, broadcasts, and message queues.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MessageBus:
    """
    Message bus for agent-to-agent communication.
    Uses Redis for reliable message delivery.
    """

    _instance = None
    _redis: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        return self._redis

    async def send(
        self,
        sender_id: uuid.UUID,
        receiver_id: uuid.UUID,
        content: str,
        message_type: str = "direct",
        metadata: Dict = None,
    ) -> Dict[str, Any]:
        """Send a direct message from one agent to another."""
        r = await self._get_redis()

        message = {
            "id": str(uuid.uuid4()),
            "sender_id": str(sender_id),
            "receiver_id": str(receiver_id),
            "content": content,
            "type": message_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        # Store in receiver's message queue
        queue_key = f"agent:messages:{receiver_id}"
        await r.lpush(queue_key, json.dumps(message))

        # Trim queue to prevent unbounded growth
        await r.ltrim(queue_key, 0, 999)

        # Publish for real-time notification
        channel = f"agent:channel:{receiver_id}"
        await r.publish(channel, json.dumps(message))

        logger.debug(
            "Message sent",
            sender=str(sender_id),
            receiver=str(receiver_id),
            type=message_type,
        )

        return message

    async def broadcast(
        self,
        sender_id: uuid.UUID,
        team_id: uuid.UUID,
        content: str,
        message_type: str = "broadcast",
        metadata: Dict = None,
    ) -> Dict[str, Any]:
        """Broadcast a message to all agents in a team."""
        r = await self._get_redis()

        message = {
            "id": str(uuid.uuid4()),
            "sender_id": str(sender_id),
            "team_id": str(team_id),
            "content": content,
            "type": message_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        # Publish to team channel
        channel = f"team:channel:{team_id}"
        await r.publish(channel, json.dumps(message))

        logger.debug(
            "Broadcast sent",
            sender=str(sender_id),
            team=str(team_id),
        )

        return message

    async def receive_for_agent(self, agent_id: uuid.UUID, limit: int = 50) -> List[Dict]:
        """Get pending messages for an agent."""
        r = await self._get_redis()

        queue_key = f"agent:messages:{agent_id}"
        messages_raw = await r.lrange(queue_key, 0, limit - 1)

        messages = []
        for raw in messages_raw:
            try:
                msg = json.loads(raw)
                messages.append(msg)
            except json.JSONDecodeError:
                continue

        # Remove retrieved messages
        if messages:
            await r.ltrim(queue_key, len(messages), -1)

        return messages

    async def subscribe_to_agent(self, agent_id: uuid.UUID):
        """Subscribe to real-time messages for an agent (async generator)."""
        r = await self._get_redis()
        pubsub = r.pubsub()

        channel = f"agent:channel:{agent_id}"
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                    except json.JSONDecodeError:
                        continue
        finally:
            await pubsub.unsubscribe(channel)

    async def subscribe_to_team(self, team_id: uuid.UUID):
        """Subscribe to team broadcast channel."""
        r = await self._get_redis()
        pubsub = r.pubsub()

        channel = f"team:channel:{team_id}"
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                    except json.JSONDecodeError:
                        continue
        finally:
            await pubsub.unsubscribe(channel)

    async def get_message_history(
        self,
        agent_id: uuid.UUID,
        other_agent_id: uuid.UUID = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Get message history between two agents or for a single agent."""
        # This could be backed by PostgreSQL for persistence
        # For now, return recent from Redis
        r = await self._get_redis()

        queue_key = f"agent:messages:{agent_id}"
        messages_raw = await r.lrange(queue_key, 0, limit - 1)

        messages = []
        for raw in messages_raw:
            try:
                msg = json.loads(raw)
                if other_agent_id is None or msg.get("sender_id") == str(other_agent_id):
                    messages.append(msg)
            except json.JSONDecodeError:
                continue

        return messages

    async def acknowledge(self, message_id: str, agent_id: uuid.UUID):
        """Acknowledge receipt of a message."""
        r = await self._get_redis()
        ack_key = f"agent:ack:{agent_id}:{message_id}"
        await r.setex(ack_key, 3600, datetime.now(timezone.utc).isoformat())
