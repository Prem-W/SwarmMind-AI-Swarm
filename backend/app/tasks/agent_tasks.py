"""
Celery tasks for agent execution.

Handles asynchronous agent task processing with retry logic,
error handling, and result storage.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from celery import states
from celery.exceptions import MaxRetriesExceededError

from app.core.config import get_settings
from app.core.exceptions import AgentExecutionException
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

settings = get_settings()
logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def execute_agent_task(self, agent_id: str, task_id: str, task_data: dict):
    """
    Execute an agent task asynchronously.
    
    Args:
        agent_id: UUID of the agent to execute the task
        task_id: UUID of the task to execute
        task_data: Task input data and configuration
    
    Returns:
        dict: Task execution result
    """
    try:
        logger.info(
            "Executing agent task",
            agent_id=agent_id,
            task_id=task_id,
            task_type=task_data.get("task_type"),
        )

        # Import here to avoid circular dependencies
        from app.services.orchestrator import SwarmOrchestrator

        # Run the async orchestrator in sync context
        orchestrator = SwarmOrchestrator()
        result = asyncio.run(
            orchestrator.execute_single_task(
                agent_id=uuid.UUID(agent_id),
                task_id=uuid.UUID(task_id),
                task_data=task_data,
            )
        )

        logger.info(
            "Agent task completed",
            agent_id=agent_id,
            task_id=task_id,
            status="success",
        )

        return {
            "status": "completed",
            "task_id": task_id,
            "agent_id": agent_id,
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    except AgentExecutionException as exc:
        logger.error(
            "Agent task failed",
            agent_id=agent_id,
            task_id=task_id,
            error=str(exc),
            retry_count=self.request.retries,
        )

        if self.request.retries < settings.max_retry_attempts:
            raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))

        return {
            "status": "failed",
            "task_id": task_id,
            "agent_id": agent_id,
            "error": str(exc),
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        logger.error(
            "Unexpected error in agent task",
            agent_id=agent_id,
            task_id=task_id,
            error=str(exc),
            exc_info=True,
        )

        if self.request.retries < settings.max_retry_attempts:
            raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1))

        return {
            "status": "failed",
            "task_id": task_id,
            "agent_id": agent_id,
            "error": f"Unexpected error: {str(exc)}",
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }


@celery_app.task
def cleanup_stale_tasks():
    """Clean up tasks that have been running too long."""
    logger.info("Running stale task cleanup")
    # Implementation for cleaning up stale tasks
    return {"cleaned": 0}


@celery_app.task
def update_agent_metrics():
    """Periodically update agent performance metrics."""
    logger.info("Updating agent metrics")
    # Implementation for metrics aggregation
    return {"updated": 0}
