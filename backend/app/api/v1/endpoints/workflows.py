"""
Workflow API Endpoints

CRUD for workflows, execution triggers, and status monitoring.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.middleware.auth import get_current_user
from app.models.execution import Execution, ExecutionStatus
from app.models.user import User
from app.models.workflow import Workflow, WorkflowStatus
from app.tasks.workflow_tasks import execute_workflow

logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["Workflows"])


class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    team_id: str
    input_data: dict = {}
    config: dict = {}
    max_parallel_agents: int = 5
    enable_dynamic_agents: bool = True
    enable_failure_recovery: bool = True
    require_human_approval: bool = False


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    team_id: str
    version: int
    is_active: bool
    created_at: str


class ExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    triggered_by: str


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    team_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
):
    """List workflows with filtering."""
    async with AsyncSessionLocal() as session:
        stmt = select(Workflow).where(Workflow.is_active == True)

        if team_id:
            stmt = stmt.where(Workflow.team_id == uuid.UUID(team_id))
        if status:
            stmt = stmt.where(Workflow.status == WorkflowStatus(status))

        result = await session.execute(stmt)
        workflows = result.scalars().all()

        return [
            WorkflowResponse(
                id=str(w.id),
                name=w.name,
                description=w.description,
                status=w.status.value,
                team_id=str(w.team_id),
                version=w.version,
                is_active=w.is_active,
                created_at=w.created_at.isoformat() if w.created_at else None,
            )
            for w in workflows
        ]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, user: User = Depends(get_current_user)):
    """Get a specific workflow."""
    async with AsyncSessionLocal() as session:
        workflow = await session.get(Workflow, uuid.UUID(workflow_id))
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return WorkflowResponse(
            id=str(workflow.id),
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            team_id=str(workflow.team_id),
            version=workflow.version,
            is_active=workflow.is_active,
            created_at=workflow.created_at.isoformat() if workflow.created_at else None,
        )


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    user: User = Depends(get_current_user),
):
    """Create a new workflow."""
    async with AsyncSessionLocal() as session:
        workflow = Workflow(
            name=request.name,
            description=request.description,
            team_id=uuid.UUID(request.team_id),
            owner_id=user.id,
            input_data=request.input_data,
            config=request.config,
            status=WorkflowStatus.DRAFT,
            max_parallel_agents=request.max_parallel_agents,
            enable_dynamic_agents=request.enable_dynamic_agents,
            enable_failure_recovery=request.enable_failure_recovery,
            require_human_approval=request.require_human_approval,
            is_active=True,
        )
        session.add(workflow)
        await session.commit()
        await session.refresh(workflow)

        logger.info("Workflow created", workflow_id=str(workflow.id), name=workflow.name)

        return WorkflowResponse(
            id=str(workflow.id),
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            team_id=str(workflow.team_id),
            version=workflow.version,
            is_active=workflow.is_active,
            created_at=workflow.created_at.isoformat() if workflow.created_at else None,
        )


@router.post("/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow_endpoint(
    workflow_id: str,
    trigger_data: Optional[dict] = None,
    user: User = Depends(get_current_user),
):
    """Trigger workflow execution."""
    async with AsyncSessionLocal() as session:
        workflow = await session.get(Workflow, uuid.UUID(workflow_id))
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Create execution record
        execution = Execution(
            workflow_id=workflow.id,
            status=ExecutionStatus.PENDING,
            triggered_by="manual",
            trigger_user_id=user.id,
            input_snapshot=trigger_data or {},
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)

        # Queue execution via Celery
        execute_workflow.delay(
            workflow_id=str(workflow.id),
            execution_id=str(execution.id),
            trigger_data=trigger_data or {},
        )

        logger.info(
            "Workflow execution queued",
            workflow_id=workflow_id,
            execution_id=str(execution.id),
        )

        return ExecutionResponse(
            id=str(execution.id),
            workflow_id=str(workflow.id),
            status=execution.status.value,
            started_at=None,
            completed_at=None,
            triggered_by=execution.triggered_by,
        )


@router.get("/{workflow_id}/executions", response_model=List[ExecutionResponse])
async def list_executions(
    workflow_id: str,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    """List executions for a workflow."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Execution)
            .where(Execution.workflow_id == uuid.UUID(workflow_id))
            .order_by(Execution.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        executions = result.scalars().all()

        return [
            ExecutionResponse(
                id=str(e.id),
                workflow_id=str(e.workflow_id),
                status=e.status.value,
                started_at=e.started_at.isoformat() if e.started_at else None,
                completed_at=e.completed_at.isoformat() if e.completed_at else None,
                triggered_by=e.triggered_by,
            )
            for e in executions
        ]


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, user: User = Depends(get_current_user)):
    """Soft delete a workflow."""
    async with AsyncSessionLocal() as session:
        workflow = await session.get(Workflow, uuid.UUID(workflow_id))
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        workflow.is_active = False
        await session.commit()

        logger.info("Workflow deactivated", workflow_id=workflow_id)
        return {"message": "Workflow deactivated"}
