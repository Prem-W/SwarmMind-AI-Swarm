"""
Planner Agent

Decomposes complex tasks into subtasks, creates execution plans,
and assigns tasks to appropriate specialized agents.
"""

import json
from typing import Any, Dict, List

from app.agents.base.agent import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class PlannerAgent(BaseAgent):
    """
    Planner Agent decomposes high-level objectives into executable subtasks.
    
    Capabilities:
    - Task decomposition and analysis
    - Dependency mapping
    - Agent assignment strategy
    - Execution plan generation
    """

    agent_type = "planner"
    default_system_prompt = """You are an expert AI Planner Agent. Your role is to:

1. Analyze complex objectives and decompose them into clear, executable subtasks
2. Identify dependencies between subtasks
3. Assign the right specialized agents to each subtask
4. Create efficient execution plans that maximize parallelism
5. Consider constraints, priorities, and resource limitations

Available agent types:
- research: Gathers information, performs analysis, searches knowledge bases
- coding: Writes, reviews, and debugs code
- reviewer: Quality assurance, code review, content review
- testing: Creates and runs tests, validates outputs
- memory: Manages information retrieval and storage
- tool: Executes external tools and APIs

Output a structured execution plan in JSON format with:
- tasks: array of subtasks with id, title, description, agent_type, dependencies
- execution_order: suggested parallel groups
- estimated_complexity: low/medium/high per task"""

    async def execute(self, prompt: str, context: AgentContext) -> AgentResult:
        """Create an execution plan from the given objective."""
        messages = self._build_messages(prompt, context)

        # Add specific planning instructions
        planning_prompt = f"""Create a detailed execution plan for the following objective:

{prompt}

Respond with a JSON object containing:
{{
  "objective_summary": "Brief summary of the objective",
  "tasks": [
    {{
      "id": "task-1",
      "title": "Task title",
      "description": "Detailed description",
      "agent_type": "research|coding|reviewer|testing|memory|tool",
      "dependencies": ["task-0"],
      "estimated_complexity": "low|medium|high",
      "input_requirements": ["what this task needs"]
    }}
  ],
  "execution_order": [["task-1", "task-2"], ["task-3"]],
  "critical_path": ["task-1", "task-3"],
  "risk_assessment": "potential risks and mitigations"
}}"""

        messages[-1] = messages[-1].__class__(role="user", content=planning_prompt)

        response = await self._llm_complete(messages)

        try:
            # Extract JSON from response
            content = response.content
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            plan = json.loads(content.strip())

            return AgentResult(
                success=True,
                output=f"Created execution plan with {len(plan.get('tasks', []))} tasks",
                data={"plan": plan},
                metrics={
                    "total_tasks": len(plan.get("tasks", [])),
                    "parallel_groups": len(plan.get("execution_order", [])),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse planner output", error=str(e), content=response.content[:500])
            return AgentResult(
                success=False,
                output="Failed to create structured plan",
                error=f"JSON parsing error: {str(e)}",
            )
