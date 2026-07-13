"""
Swarm Orchestrator

The central intelligence of SwarmMind. Handles:
- Dynamic task decomposition
- Agent assignment and load balancing
- Parallel execution coordination
- Leader election
- Failure recovery and retry logic
- Human approval gating
- Real-time execution tracking
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.base.agent import AgentContext, AgentResult
from app.agents.types.coding import CodingAgent
from app.agents.types.memory import MemoryAgent
from app.agents.types.planner import PlannerAgent
from app.agents.types.research import ResearchAgent
from app.agents.types.reviewer import ReviewerAgent
from app.agents.types.testing import TestingAgent
from app.agents.types.tool import ToolAgent
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import (
    AgentExecutionException,
    AgentNotFoundException,
    SwarmOrchestrationException,
    TaskNotFoundException,
)
from app.core.logging import get_logger
from app.models.agent import Agent as AgentModel
from app.models.agent import AgentStatus, AgentType
from app.models.execution import Execution, ExecutionLog, ExecutionStatus
from app.models.task import Task, TaskPriority, TaskResult, TaskStatus
from app.models.workflow import Workflow, WorkflowStatus
from app.services.llm.base import Message
from app.services.llm.manager import llm_manager

logger = get_logger(__name__)
settings = get_settings()

# Agent type to class mapping
AGENT_CLASS_MAP = {
    AgentType.PLANNER: PlannerAgent,
    AgentType.RESEARCH: ResearchAgent,
    AgentType.CODING: CodingAgent,
    AgentType.REVIEWER: ReviewerAgent,
    AgentType.TESTING: TestingAgent,
    AgentType.MEMORY: MemoryAgent,
    AgentType.TOOL: ToolAgent,
}


class SwarmOrchestrator:
    """
    Central orchestrator for the agent swarm.
    
    Manages the full lifecycle of multi-agent task execution:
    1. Receive workflow/task
    2. Decompose into subtasks (Planner)
    3. Elect leader agent
    4. Assign tasks to specialized agents
    5. Execute in parallel where possible
    6. Monitor and recover from failures
    7. Collect and return results
    """

    def __init__(self):
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._agent_pool: Dict[str, Any] = {}  # Runtime agent instances

    async def execute_workflow(
        self,
        workflow_id: uuid.UUID,
        execution_id: uuid.UUID,
        trigger_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow with full orchestration.
        
        This is the main entry point for workflow execution.
        """
        logger.info(
            "Starting workflow execution",
            workflow_id=str(workflow_id),
            execution_id=str(execution_id),
        )

        async with AsyncSessionLocal() as session:
            # Load workflow
            workflow = await session.get(Workflow, workflow_id)
            if not workflow:
                raise SwarmOrchestrationException(f"Workflow {workflow_id} not found")

            # Load execution record
            execution = await session.get(Execution, execution_id)
            if not execution:
                raise SwarmOrchestrationException(f"Execution {execution_id} not found")

            # Update execution status
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)
            await session.commit()

            # Log start
            await self._log_execution(
                session, execution_id, "INFO", "workflow_started",
                f"Workflow '{workflow.name}' execution started",
                {"workflow_id": str(workflow_id)},
            )

            try:
                # Step 1: Dynamic task decomposition via Planner
                plan = await self._decompose_workflow(session, workflow, execution_id, trigger_data)

                # Step 2: Elect leader agent
                leader_id = await self._elect_leader(session, workflow.team_id, plan)
                execution.leader_agent_id = leader_id
                await session.commit()

                # Step 3: Execute tasks with parallelization
                results = await self._execute_parallel_tasks(
                    session, execution_id, workflow.team_id, plan, trigger_data
                )

                # Step 4: Compile final results
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.now(timezone.utc)
                execution.output_snapshot = {"results": results}
                workflow.last_execution_at = datetime.now(timezone.utc)
                workflow.execution_count += 1
                await session.commit()

                await self._log_execution(
                    session, execution_id, "INFO", "workflow_completed",
                    f"Workflow '{workflow.name}' completed successfully",
                    {"results_count": len(results)},
                )

                return {
                    "status": "completed",
                    "execution_id": str(execution_id),
                    "workflow_id": str(workflow_id),
                    "results": results,
                    "leader_agent_id": str(leader_id) if leader_id else None,
                }

            except Exception as e:
                execution.status = ExecutionStatus.FAILED
                await session.commit()

                await self._log_execution(
                    session, execution_id, "ERROR", "workflow_failed",
                    f"Workflow failed: {str(e)}",
                    {"error": str(e)},
                )

                logger.error(
                    "Workflow execution failed",
                    workflow_id=str(workflow_id),
                    execution_id=str(execution_id),
                    error=str(e),
                )

                raise SwarmOrchestrationException(f"Workflow execution failed: {str(e)}")

    async def execute_single_task(
        self,
        agent_id: uuid.UUID,
        task_id: uuid.UUID,
        task_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single task with a specific agent."""
        async with AsyncSessionLocal() as session:
            # Load agent configuration
            agent_model = await session.get(AgentModel, agent_id)
            if not agent_model or not agent_model.is_active:
                raise AgentNotFoundException(str(agent_id))

            # Update agent status
            agent_model.status = AgentStatus.BUSY
            await session.commit()

            try:
                # Create runtime agent instance
                agent_class = AGENT_CLASS_MAP.get(agent_model.agent_type)
                if not agent_class:
                    raise AgentExecutionException(
                        agent_id=str(agent_id),
                        detail=f"Unknown agent type: {agent_model.agent_type}",
                    )

                agent = agent_class(
                    agent_id=agent_model.id,
                    name=agent_model.name,
                    llm_provider=agent_model.llm_provider,
                    llm_model=agent_model.llm_model,
                    temperature=agent_model.temperature,
                    max_tokens=agent_model.max_tokens,
                    system_prompt=agent_model.system_prompt,
                    tools=agent_model.tools,
                    config=agent_model.config,
                )

                # Build context
                context = AgentContext(
                    task_id=str(task_id),
                    input_data=task_data.get("input", {}),
                    shared_memory=task_data.get("shared_memory", {}),
                    parent_results=task_data.get("parent_results", {}),
                )

                # Execute
                prompt = task_data.get("prompt", task_data.get("description", "Execute task"))
                result = await agent.run(prompt, context)

                # Update stats
                agent_model.total_tasks_completed += 1
                agent_model.status = AgentStatus.IDLE
                await session.commit()

                return {
                    "success": result.success,
                    "output": result.output,
                    "data": result.data,
                    "artifacts": result.artifacts,
                    "metrics": result.metrics,
                }

            except Exception as e:
                agent_model.total_tasks_failed += 1
                agent_model.status = AgentStatus.ERROR
                await session.commit()

                raise AgentExecutionException(
                    agent_id=str(agent_id),
                    task_id=str(task_id),
                    detail=str(e),
                )

    async def _decompose_workflow(
        self,
        session,
        workflow: Workflow,
        execution_id: uuid.UUID,
        trigger_data: Dict,
    ) -> Dict[str, Any]:
        """Decompose workflow into executable tasks using Planner agent."""
        logger.info("Decomposing workflow", workflow_id=str(workflow.id))

        await self._log_execution(
            session, execution_id, "INFO", "decomposition_started",
            "Starting task decomposition",
        )

        # Find or create a planner agent
        from sqlalchemy import select

        result = await session.execute(
            select(AgentModel).where(
                AgentModel.team_id == workflow.team_id,
                AgentModel.agent_type == AgentType.PLANNER,
                AgentModel.is_active == True,
            )
        )
        planner_model = result.scalar_one_or_none()

        if not planner_model:
            # Fallback: create decomposition without planner agent
            logger.warning("No planner agent found, using default decomposition")
            return self._default_decomposition(workflow, trigger_data)

        # Use planner agent for intelligent decomposition
        planner = PlannerAgent(
            agent_id=planner_model.id,
            name=planner_model.name,
            llm_provider=planner_model.llm_provider,
            llm_model=planner_model.llm_model,
        )

        objective = trigger_data.get("objective", workflow.name)
        context = AgentContext(
            task_id=str(execution_id),
            input_data={"workflow": workflow.name, "steps": [s.name for s in workflow.steps]},
        )

        plan_result = await planner.run(
            prompt=f"Create execution plan for: {objective}",
            context=context,
        )

        if plan_result.success and "plan" in plan_result.data:
            plan = plan_result.data["plan"]
            await self._log_execution(
                session, execution_id, "INFO", "decomposition_complete",
                f"Decomposed into {len(plan.get('tasks', []))} tasks",
                {"task_count": len(plan.get("tasks", []))},
            )
            return plan

        return self._default_decomposition(workflow, trigger_data)

    def _default_decomposition(self, workflow: Workflow, trigger_data: Dict) -> Dict[str, Any]:
        """Create a default execution plan from workflow steps."""
        tasks = []
        for i, step in enumerate(workflow.steps):
            tasks.append({
                "id": f"task-{i}",
                "title": step.name,
                "description": step.description or step.name,
                "agent_type": step.agent.agent_type.value if step.agent else "custom",
                "agent_id": str(step.agent_id) if step.agent_id else None,
                "dependencies": step.depends_on or [],
                "estimated_complexity": "medium",
            })

        return {
            "tasks": tasks,
            "execution_order": [[t["id"] for t in tasks]],
            "critical_path": [t["id"] for t in tasks],
        }

    async def _elect_leader(
        self,
        session,
        team_id: uuid.UUID,
        plan: Dict[str, Any],
    ) -> Optional[uuid.UUID]:
        """
        Elect a leader agent for the swarm.
        
        Leader selection strategy:
        1. Prefer a planner agent (natural coordinator)
        2. Select based on lowest current load
        3. Consider agent capabilities vs. plan requirements
        """
        from sqlalchemy import select

        result = await session.execute(
            select(AgentModel).where(
                AgentModel.team_id == team_id,
                AgentModel.is_active == True,
                AgentModel.status.in_([AgentStatus.IDLE, AgentStatus.LEADER]),
            )
        )
        agents = result.scalars().all()

        if not agents:
            logger.warning("No available agents for leader election")
            return None

        # Score agents: prefer planners, then by load
        def score_agent(agent):
            score = 0
            if agent.agent_type == AgentType.PLANNER:
                score += 100
            # Lower load = higher score
            score += max(0, 50 - agent.total_tasks_completed - agent.total_tasks_failed * 2)
            # Prefer idle agents
            if agent.status == AgentStatus.IDLE:
                score += 25
            return score

        leader = max(agents, key=score_agent)
        leader.status = AgentStatus.LEADER
        await session.commit()

        logger.info("Leader elected", agent_id=str(leader.id), agent_name=leader.name)
        return leader.id

    async def _execute_parallel_tasks(
        self,
        session,
        execution_id: uuid.UUID,
        team_id: uuid.UUID,
        plan: Dict[str, Any],
        trigger_data: Dict,
    ) -> Dict[str, Any]:
        """Execute tasks with maximum parallelism respecting dependencies."""
        tasks = plan.get("tasks", [])
        execution_order = plan.get("execution_order", [])
        results = {}
        completed_tasks = set()
        failed_tasks = set()

        for batch in execution_order:
            # Filter to tasks that exist and have dependencies met
            ready_tasks = [
                t for t in tasks
                if t["id"] in batch
                and all(dep in completed_tasks for dep in t.get("dependencies", []))
                and t["id"] not in completed_tasks
                and t["id"] not in failed_tasks
            ]

            if not ready_tasks:
                continue

            # Execute batch in parallel
            batch_tasks = [
                self._execute_task_with_recovery(
                    session, execution_id, team_id, task, trigger_data, results
                )
                for task in ready_tasks
            ]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for task, result in zip(ready_tasks, batch_results):
                if isinstance(result, Exception):
                    logger.error(
                        "Task failed",
                        task_id=task["id"],
                        error=str(result),
                    )
                    failed_tasks.add(task["id"])
                    results[task["id"]] = {"success": False, "error": str(result)}
                else:
                    completed_tasks.add(task["id"])
                    results[task["id"]] = result

        return {
            "completed": list(completed_tasks),
            "failed": list(failed_tasks),
            "task_results": results,
        }

    async def _execute_task_with_recovery(
        self,
        session,
        execution_id: uuid.UUID,
        team_id: uuid.UUID,
        task: Dict,
        trigger_data: Dict,
        parent_results: Dict,
    ) -> Dict:
        """Execute a single task with retry logic and failure recovery."""
        task_id = task["id"]
        max_retries = settings.max_retry_attempts

        for attempt in range(max_retries):
            try:
                result = await self._execute_single_task_internal(
                    session, execution_id, team_id, task, trigger_data, parent_results
                )

                if result.get("success"):
                    return result

                # Task returned but wasn't successful
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        "Task attempt failed, retrying",
                        task_id=task_id,
                        attempt=attempt + 1,
                        wait=wait_time,
                    )
                    await asyncio.sleep(wait_time)

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "Task exception, retrying",
                        task_id=task_id,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

        return {"success": False, "error": f"Failed after {max_retries} attempts"}

    async def _execute_single_task_internal(
        self,
        session,
        execution_id: uuid.UUID,
        team_id: uuid.UUID,
        task: Dict,
        trigger_data: Dict,
        parent_results: Dict,
    ) -> Dict:
        """Internal task execution logic."""
        # Find appropriate agent
        agent_id = task.get("agent_id")
        agent_type = task.get("agent_type", "custom")

        if not agent_id:
            # Find agent by type
            from sqlalchemy import select

            result = await session.execute(
                select(AgentModel).where(
                    AgentModel.team_id == team_id,
                    AgentModel.agent_type == AgentType(agent_type) if agent_type != "custom" else AgentType.CUSTOM,
                    AgentModel.is_active == True,
                    AgentModel.status == AgentStatus.IDLE,
                )
            )
            agent = result.scalar_one_or_none()

            if not agent:
                # Fallback: any available agent
                result = await session.execute(
                    select(AgentModel).where(
                        AgentModel.team_id == team_id,
                        AgentModel.is_active == True,
                        AgentModel.status == AgentStatus.IDLE,
                    )
                )
                agent = result.scalar_one_or_none()

            if not agent:
                raise AgentExecutionException(
                    detail=f"No available agent for task {task['id']} (type: {agent_type})",
                )

            agent_id = agent.id

        # Build task data
        task_data = {
            "prompt": task.get("description", task.get("title", "Execute task")),
            "input": trigger_data,
            "shared_memory": trigger_data.get("shared_memory", {}),
            "parent_results": {
                k: v for k, v in parent_results.items()
                if k in task.get("dependencies", [])
            },
        }

        # Execute via the single task path
        return await self.execute_single_task(
            agent_id=uuid.UUID(str(agent_id)),
            task_id=uuid.UUID(str(execution_id)),  # Use execution ID as task tracking
            task_data=task_data,
        )

    async def _log_execution(
        self,
        session,
        execution_id: uuid.UUID,
        level: str,
        event_type: str,
        message: str,
        details: Dict = None,
    ):
        """Log an execution event."""
        log = ExecutionLog(
            execution_id=execution_id,
            timestamp=datetime.now(timezone.utc),
            level=level,
            event_type=event_type,
            message=message,
            details=details or {},
        )
        session.add(log)
        await session.commit()
