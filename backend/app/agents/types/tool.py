"""
Tool Agent

Executes external tools, APIs, and integrations.
"""

import json
from typing import Any, Dict

from app.agents.base.agent import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class ToolAgent(BaseAgent):
    """
    Tool Agent executes external tools and APIs.
    
    Capabilities:
    - API calls and data retrieval
    - File operations
    - Database queries
    - External service integration
    - Data transformation
    """

    agent_type = "tool"
    default_system_prompt = """You are an expert AI Tool Agent. Your role is to:

1. Execute external tools and APIs effectively
2. Handle API authentication and error responses
3. Transform data between formats
4. Integrate with external services
5. Report tool execution results clearly

When using tools:
- Always handle errors gracefully
- Validate inputs before sending to APIs
- Parse and structure responses consistently
- Respect rate limits and quotas
- Log tool usage for debugging"""

    async def execute(self, prompt: str, context: AgentContext) -> AgentResult:
        """Execute tool operation."""
        messages = self._build_messages(prompt, context)

        tool_prompt = f"""Analyze the following request and determine the best tool/approach:

{prompt}

Provide:
1. **Tool Selection**: Which tool or API to use
2. **Execution Plan**: Step-by-step plan
3. **Request Details**: Specific API calls or commands needed
4. **Expected Response**: What to expect from the tool
5. **Error Handling**: How to handle potential failures

If this involves HTTP requests, provide the full request details (method, URL, headers, body).
If this involves file operations, specify the exact file paths and formats."""

        messages[-1] = messages[-1].__class__(role="user", content=tool_prompt)

        response = await self._llm_complete(messages)

        return AgentResult(
            success=True,
            output=response.content,
            data={
                "tool_plan": response.content,
            },
            metrics={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
