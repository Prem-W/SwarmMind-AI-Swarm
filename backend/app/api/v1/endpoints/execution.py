"""
Execution API Endpoints

Real-time execution monitoring, logs, and control.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.middleware.auth import get_current_user
from app.models.execution import Execution, ExecutionLog, ExecutionStatus
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(prefix="/executions", tags=["Executions"])


class ExecutionLogResponse(BaseModel):
    id: str
    timestamp: str
    level: str
    event_type: str
    message: str
    agent_id: Optional[str]
    task_id: Optional[str]
    details: dict


class ExecutionDetailResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    total_duration_ms: int
    triggered_by: str
    metrics: dict
    agent_ids: List[str]
    leader_agent_id: Optional[str]


@router.get("/{execution_id}", response_model=ExecutionDetailResponse)
async def get_execution(execution_id: str, user: User = Depends(get_current_user)):
    """Get execution details."""
    async with AsyncSessionLocal() as session:
        execution = await session.get(Execution, uuid.UUID(execution_id))
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return ExecutionDetailResponse(
            id=str(execution.id),
            workflow_id=str(execution.workflow_id),
            status=execution.status.value,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            total_duration_ms=execution.total_duration_ms,
            triggered_by=execution.triggered_by,
            metrics=execution.metrics,
            agent_ids=[str(aid) for aid in execution.agent_ids],
            leader_agent_id=str(execution.leader_agent_id) if execution.leader_agent_id else None,
        )


@router.get("/{execution_id}/logs", response_model=List[ExecutionLogResponse])
async def get_execution_logs(
    execution_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    level: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    """Get execution logs with filtering."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == uuid.UUID(execution_id))
            .order_by(ExecutionLog.timestamp)
            .offset(offset)
            .limit(limit)
        )

        if level:
            stmt = stmt.where(ExecutionLog.level == level.upper())

        result = await session.execute(stmt)
        logs = result.scalars().all()

        return [
            ExecutionLogResponse(
                id=str(log.id),
                timestamp=log.timestamp.isoformat() if log.timestamp else None,
                level=log.level,
                event_type=log.event_type,
                message=log.message,
                agent_id=str(log.agent_id) if log.agent_id else None,
                task_id=str(log.task_id) if log.task_id else None,
                details=log.details,
            )
            for log in logs
        ]


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str, user: User = Depends(get_current_user)):
    """Cancel a running execution."""
    async with AsyncSessionLocal() as session:
        execution = await session.get(Execution, uuid.UUID(execution_id))
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            raise HTTPException(status_code=400, detail="Execution cannot be cancelled")

        execution.status = ExecutionStatus.CANCELLED
        await session.commit()

        logger.info("Execution cancelled", execution_id=execution_id, user_id=str(user.id))
        return {"message": "Execution cancelled"}


@router.get("", response_model=List[ExecutionDetailResponse])
async def list_executions(
    workflow_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    """List executions with filtering."""
    async with AsyncSessionLocal() as session:
        stmt = select(Execution).order_by(Execution.created_at.desc()).limit(limit)

        if workflow_id:
            stmt = stmt.where(Execution.workflow_id == uuid.UUID(workflow_id))
        if status:
            stmt = stmt.where(Execution.status == ExecutionStatus(status))

        result = await session.execute(stmt)
        executions = result.scalars().all()

        return [
            ExecutionDetailResponse(
                id=str(e.id),
                workflow_id=str(e.workflow_id),
                status=e.status.value,
                started_at=e.started_at.isoformat() if e.started_at else None,
                completed_at=e.completed_at.isoformat() if e.completed_at else None,
                total_duration_ms=e.total_duration_ms,
                triggered_by=e.triggered_by,
                metrics=e.metrics,
                agent_ids=[str(aid) for aid in e.agent_ids],
                leader_agent_id=str(e.leader_agent_id) if e.leader_agent_id else None,
            )
            for e in executions
        ]
