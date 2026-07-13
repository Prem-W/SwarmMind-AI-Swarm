"""
Agent Management API Endpoints

CRUD operations for agents, agent status, and agent configuration.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.middleware.auth import get_current_user, require_admin
from app.models.agent import Agent, AgentStatus, AgentType
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["Agents"])


class AgentCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    agent_type: str
    team_id: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: Optional[str] = None
    tools: List[str] = []
    capabilities: List[str] = []
    config: dict = {}


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    agent_type: str
    status: str
    team_id: str
    llm_provider: str
    llm_model: str
    temperature: float
    max_tokens: int
    tools: List[str]
    capabilities: List[str]
    total_tasks_completed: int
    total_tasks_failed: int
    is_active: bool
    created_at: str


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    team_id: Optional[str] = Query(None),
    agent_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    """List agents with optional filtering."""
    async with AsyncSessionLocal() as session:
        stmt = select(Agent).where(Agent.is_active == True)

        if team_id:
            stmt = stmt.where(Agent.team_id == uuid.UUID(team_id))
        if agent_type:
            stmt = stmt.where(Agent.agent_type == AgentType(agent_type))
        if status:
            stmt = stmt.where(Agent.status == AgentStatus(status))

        result = await session.execute(stmt)
        agents = result.scalars().all()

        return [
            AgentResponse(
                id=str(a.id),
                name=a.name,
                description=a.description,
                agent_type=a.agent_type.value,
                status=a.status.value,
                team_id=str(a.team_id),
                llm_provider=a.llm_provider,
                llm_model=a.llm_model,
                temperature=a.temperature,
                max_tokens=a.max_tokens,
                tools=a.tools,
                capabilities=a.capabilities,
                total_tasks_completed=a.total_tasks_completed,
                total_tasks_failed=a.total_tasks_failed,
                is_active=a.is_active,
                created_at=a.created_at.isoformat() if a.created_at else None,
            )
            for a in agents
        ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, user: User = Depends(get_current_user)):
    """Get a specific agent by ID."""
    async with AsyncSessionLocal() as session:
        agent = await session.get(Agent, uuid.UUID(agent_id))
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        return AgentResponse(
            id=str(agent.id),
            name=agent.name,
            description=agent.description,
            agent_type=agent.agent_type.value,
            status=agent.status.value,
            team_id=str(agent.team_id),
            llm_provider=agent.llm_provider,
            llm_model=agent.llm_model,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            tools=agent.tools,
            capabilities=agent.capabilities,
            total_tasks_completed=agent.total_tasks_completed,
            total_tasks_failed=agent.total_tasks_failed,
            is_active=agent.is_active,
            created_at=agent.created_at.isoformat() if agent.created_at else None,
        )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(request: AgentCreateRequest, user: User = Depends(get_current_user)):
    """Create a new agent."""
    async with AsyncSessionLocal() as session:
        agent = Agent(
            name=request.name,
            description=request.description,
            agent_type=AgentType(request.agent_type),
            team_id=uuid.UUID(request.team_id),
            owner_id=user.id,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
            tools=request.tools,
            capabilities=request.capabilities,
            config=request.config,
            status=AgentStatus.IDLE,
            is_active=True,
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        logger.info("Agent created", agent_id=str(agent.id), name=agent.name, type=agent.agent_type.value)

        return AgentResponse(
            id=str(agent.id),
            name=agent.name,
            description=agent.description,
            agent_type=agent.agent_type.value,
            status=agent.status.value,
            team_id=str(agent.team_id),
            llm_provider=agent.llm_provider,
            llm_model=agent.llm_model,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            tools=agent.tools,
            capabilities=agent.capabilities,
            total_tasks_completed=0,
            total_tasks_failed=0,
            is_active=agent.is_active,
            created_at=agent.created_at.isoformat() if agent.created_at else None,
        )


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    user: User = Depends(get_current_user),
):
    """Update an agent's configuration."""
    async with AsyncSessionLocal() as session:
        agent = await session.get(Agent, uuid.UUID(agent_id))
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(agent, field, value)

        await session.commit()
        await session.refresh(agent)

        return AgentResponse(
            id=str(agent.id),
            name=agent.name,
            description=agent.description,
            agent_type=agent.agent_type.value,
            status=agent.status.value,
            team_id=str(agent.team_id),
            llm_provider=agent.llm_provider,
            llm_model=agent.llm_model,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            tools=agent.tools,
            capabilities=agent.capabilities,
            total_tasks_completed=agent.total_tasks_completed,
            total_tasks_failed=agent.total_tasks_failed,
            is_active=agent.is_active,
            created_at=agent.created_at.isoformat() if agent.created_at else None,
        )


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, user: User = Depends(require_admin)):
    """Soft delete an agent."""
    async with AsyncSessionLocal() as session:
        agent = await session.get(Agent, uuid.UUID(agent_id))
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        agent.is_active = False
        await session.commit()

        logger.info("Agent deactivated", agent_id=agent_id)
        return {"message": "Agent deactivated successfully"}
