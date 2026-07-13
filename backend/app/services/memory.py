"""
Memory Service

Manages the swarm's collective memory using PostgreSQL for metadata
and Qdrant for vector embeddings.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.memory import MemoryEntry, MemoryType
from app.services.llm.manager import llm_manager

logger = get_logger(__name__)
settings = get_settings()


class MemoryService:
    """Service for managing agent and swarm memory."""

    def __init__(self):
        self.qdrant: Optional[AsyncQdrantClient] = None
        self._initialized = False

    async def _init_qdrant(self):
        """Initialize Qdrant client and collection."""
        if self._initialized:
            return

        self.qdrant = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
        )

        # Ensure collection exists
        try:
            collections = await self.qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]

            if settings.qdrant_collection not in collection_names:
                await self.qdrant.create_collection(
                    collection_name=settings.qdrant_collection,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
                logger.info("Created Qdrant collection", collection=settings.qdrant_collection)
        except Exception as e:
            logger.warning("Qdrant initialization warning", error=str(e))

        self._initialized = True

    async def store(
        self,
        content: str,
        agent_id: uuid.UUID = None,
        team_id: uuid.UUID = None,
        task_id: uuid.UUID = None,
        execution_id: uuid.UUID = None,
        memory_type: str = "short_term",
        importance: float = 1.0,
        tags: List[str] = None,
        metadata: Dict = None,
        expires_at: datetime = None,
    ) -> Dict[str, Any]:
        """Store a memory entry with vector embedding."""
        await self._init_qdrant()

        # Generate embedding
        try:
            embeddings = await llm_manager.embed([content])
            embedding = embeddings[0] if embeddings else None
        except Exception as e:
            logger.warning("Failed to generate embedding", error=str(e))
            embedding = None

        # Store in Qdrant
        embedding_id = None
        if embedding and self.qdrant:
            embedding_id = str(uuid.uuid4())
            try:
                await self.qdrant.upsert(
                    collection_name=settings.qdrant_collection,
                    points=[
                        PointStruct(
                            id=embedding_id,
                            vector=embedding,
                            payload={
                                "content": content[:1000],
                                "agent_id": str(agent_id) if agent_id else None,
                                "team_id": str(team_id) if team_id else None,
                                "memory_type": memory_type,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    ],
                )
            except Exception as e:
                logger.warning("Failed to store in Qdrant", error=str(e))
                embedding_id = None

        # Store in PostgreSQL
        async with AsyncSessionLocal() as session:
            entry = MemoryEntry(
                content=content,
                memory_type=MemoryType(memory_type),
                agent_id=agent_id,
                team_id=team_id,
                task_id=task_id,
                execution_id=execution_id,
                embedding_id=embedding_id,
                embedding_model="text-embedding-3-small" if embedding else None,
                importance=importance,
                tags=tags or [],
                metadata=metadata or {},
                expires_at=expires_at,
            )
            session.add(entry)
            await session.commit()

            logger.info(
                "Memory stored",
                memory_id=str(entry.id),
                memory_type=memory_type,
                has_embedding=embedding_id is not None,
            )

            return {
                "id": str(entry.id),
                "embedding_id": embedding_id,
                "memory_type": memory_type,
                "content_preview": content[:200],
            }

    async def search(
        self,
        query: str = None,
        agent_id: uuid.UUID = None,
        team_id: uuid.UUID = None,
        memory_type: str = None,
        limit: int = 10,
        use_vector_search: bool = True,
    ) -> List[Dict]:
        """Search memory entries with optional vector similarity."""
        await self._init_qdrant()

        results = []

        # Vector search via Qdrant
        if use_vector_search and query and self.qdrant:
            try:
                embeddings = await llm_manager.embed([query])
                if embeddings:
                    search_result = await self.qdrant.search(
                        collection_name=settings.qdrant_collection,
                        query_vector=embeddings[0],
                        limit=limit,
                        query_filter=self._build_filter(agent_id, team_id, memory_type),
                    )

                    for point in search_result:
                        results.append({
                            "id": point.id,
                            "content": point.payload.get("content", ""),
                            "score": point.score,
                            "memory_type": point.payload.get("memory_type", "unknown"),
                            "agent_id": point.payload.get("agent_id"),
                            "timestamp": point.payload.get("timestamp"),
                        })
            except Exception as e:
                logger.warning("Vector search failed, falling back to text search", error=str(e))

        # Fallback or supplement with database query
        if not results:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select, desc

                stmt = select(MemoryEntry)

                if agent_id:
                    stmt = stmt.where(MemoryEntry.agent_id == agent_id)
                if team_id:
                    stmt = stmt.where(MemoryEntry.team_id == team_id)
                if memory_type:
                    stmt = stmt.where(MemoryEntry.memory_type == MemoryType(memory_type))

                stmt = stmt.order_by(desc(MemoryEntry.created_at)).limit(limit)
                result = await session.execute(stmt)
                entries = result.scalars().all()

                results = [
                    {
                        "id": str(e.id),
                        "content": e.content,
                        "memory_type": e.memory_type.value,
                        "agent_id": str(e.agent_id) if e.agent_id else None,
                        "importance": e.importance,
                        "created_at": e.created_at.isoformat() if e.created_at else None,
                        "tags": e.tags,
                    }
                    for e in entries
                ]

        return results

    def _build_filter(self, agent_id, team_id, memory_type):
        """Build Qdrant filter from parameters."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        conditions = []

        if agent_id:
            conditions.append(
                FieldCondition(key="agent_id", match=MatchValue(value=str(agent_id)))
            )
        if memory_type:
            conditions.append(
                FieldCondition(key="memory_type", match=MatchValue(value=memory_type))
            )

        return Filter(must=conditions) if conditions else None

    async def get_by_id(self, memory_id: uuid.UUID) -> Optional[Dict]:
        """Get a specific memory entry."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(MemoryEntry).where(MemoryEntry.id == memory_id)
            )
            entry = result.scalar_one_or_none()

            if entry:
                return {
                    "id": str(entry.id),
                    "content": entry.content,
                    "memory_type": entry.memory_type.value,
                    "agent_id": str(entry.agent_id) if entry.agent_id else None,
                    "importance": entry.importance,
                    "tags": entry.tags,
                    "metadata": entry.metadata,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                }
            return None

    async def delete(self, memory_id: uuid.UUID) -> bool:
        """Delete a memory entry."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select, delete

            result = await session.execute(
                select(MemoryEntry).where(MemoryEntry.id == memory_id)
            )
            entry = result.scalar_one_or_none()

            if not entry:
                return False

            # Delete from Qdrant if embedding exists
            if entry.embedding_id and self.qdrant:
                try:
                    await self.qdrant.delete(
                        collection_name=settings.qdrant_collection,
                        points_selector=[entry.embedding_id],
                    )
                except Exception as e:
                    logger.warning("Failed to delete from Qdrant", error=str(e))

            await session.delete(entry)
            await session.commit()

            return True

    async def cleanup_expired(self) -> int:
        """Remove expired short-term memories."""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import delete, select

            result = await session.execute(
                select(MemoryEntry).where(
                    MemoryEntry.expires_at < datetime.now(timezone.utc),
                    MemoryEntry.memory_type == MemoryType.SHORT_TERM,
                )
            )
            expired = result.scalars().all()

            count = 0
            for entry in expired:
                if entry.embedding_id and self.qdrant:
                    try:
                        await self.qdrant.delete(
                            collection_name=settings.qdrant_collection,
                            points_selector=[entry.embedding_id],
                        )
                    except Exception:
                        pass
                await session.delete(entry)
                count += 1

            await session.commit()
            logger.info("Cleaned up expired memories", count=count)
            return count
