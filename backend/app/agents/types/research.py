"""
Research Agent

Performs deep research, information gathering, analysis,
and knowledge synthesis across various domains.
"""

import json
from typing import Any, Dict

from app.agents.base.agent import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class ResearchAgent(BaseAgent):
    """
    Research Agent gathers and synthesizes information.
    
    Capabilities:
    - Deep research on any topic
    - Information synthesis and summarization
    - Comparative analysis
    - Fact-checking
    - Source evaluation
    """

    agent_type = "research"
    default_system_prompt = """You are an expert AI Research Agent. Your role is to:

1. Conduct thorough research on given topics
2. Gather relevant information from your training knowledge
3. Synthesize findings into clear, actionable insights
4. Provide well-structured reports with sources and reasoning
5. Identify gaps in information and suggest follow-up research

Always structure your research with:
- Executive Summary
- Key Findings (with confidence levels)
- Detailed Analysis
- Sources and References
- Recommendations
- Areas for Further Investigation

Be thorough, objective, and cite specific details."""

    async def execute(self, prompt: str, context: AgentContext) -> AgentResult:
        """Execute research task."""
        messages = self._build_messages(prompt, context)

        research_prompt = f"""Conduct comprehensive research on the following topic/query:

{prompt}

Provide a well-structured research report with:
1. Executive Summary (2-3 sentences)
2. Key Findings (bullet points with confidence levels: high/medium/low)
3. Detailed Analysis (organized by sub-topics)
4. Implications and Recommendations
5. Areas Needing Further Investigation

Be specific, detailed, and thorough. Include concrete facts, figures, and examples where relevant."""

        messages[-1] = messages[-1].__class__(role="user", content=research_prompt)

        response = await self._llm_complete(messages)

        return AgentResult(
            success=True,
            output=response.content,
            data={
                "research_output": response.content,
                "topic": prompt[:200],
            },
            metrics={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
