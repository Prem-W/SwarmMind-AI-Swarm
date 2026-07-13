"""
Reviewer Agent

Reviews code, content, and outputs for quality, correctness,
security, and best practices.
"""

from app.agents.base.agent import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReviewerAgent(BaseAgent):
    """
    Reviewer Agent performs quality assurance reviews.
    
    Capabilities:
    - Code review (style, bugs, security, performance)
    - Content review (accuracy, clarity, completeness)
    - Output validation
    - Best practices verification
    - Security audit
    """

    agent_type = "reviewer"
    default_system_prompt = """You are an expert AI Reviewer Agent. Your role is to:

1. Thoroughly review code, content, and outputs for quality
2. Identify bugs, security vulnerabilities, and performance issues
3. Check adherence to best practices and standards
4. Verify correctness and completeness
5. Provide actionable, constructive feedback

When reviewing, always check for:
- **Correctness**: Does it work as intended?
- **Security**: Are there vulnerabilities?
- **Performance**: Are there inefficiencies?
- **Maintainability**: Is it readable and well-structured?
- **Edge Cases**: Are boundary conditions handled?
- **Standards**: Does it follow conventions?

Provide a clear verdict: APPROVED, NEEDS_CHANGES, or REJECTED with specific reasons."""

    async def execute(self, prompt: str, context: AgentContext) -> AgentResult:
        """Execute review task."""
        messages = self._build_messages(prompt, context)

        review_prompt = f"""Please review the following content/code and provide a comprehensive assessment:

{prompt}

Structure your review as follows:

## Verdict
- **Status**: APPROVED / NEEDS_CHANGES / REJECTED
- **Overall Score**: X/10

## Summary
Brief overview of the quality assessment

## Detailed Findings

### Correctness
- Issues found (if any)

### Security
- Vulnerabilities or concerns

### Performance
- Efficiency observations

### Maintainability
- Code quality and readability

### Best Practices
- Standards compliance

## Action Items
1. [Priority: High/Medium/Low] Specific change needed

## Positive Aspects
What was done well"""

        messages[-1] = messages[-1].__class__(role="user", content=review_prompt)

        response = await self._llm_complete(messages)

        # Parse verdict from response
        verdict = "NEEDS_CHANGES"
        if "APPROVED" in response.content[:500]:
            verdict = "APPROVED"
        elif "REJECTED" in response.content[:500]:
            verdict = "REJECTED"

        return AgentResult(
            success=True,
            output=response.content,
            data={
                "verdict": verdict,
                "review": response.content,
                "approved": verdict == "APPROVED",
            },
            metrics={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
