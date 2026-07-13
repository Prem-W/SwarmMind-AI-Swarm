"""
Testing Agent

Creates and runs tests, validates outputs, and ensures quality.
"""

from app.agents.base.agent import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class TestingAgent(BaseAgent):
    """
    Testing Agent creates and validates tests.
    
    Capabilities:
    - Unit test generation
    - Integration test creation
    - Test case design
    - Output validation
    - Edge case identification
    """

    agent_type = "testing"
    default_system_prompt = """You are an expert AI Testing Agent. Your role is to:

1. Create comprehensive test suites for code and systems
2. Design test cases that cover happy paths, edge cases, and error scenarios
3. Validate outputs against expected results
4. Identify missing test coverage
5. Ensure quality and reliability

When creating tests:
- Cover normal operations, boundaries, and error conditions
- Include both positive and negative test cases
- Write clear test descriptions
- Use appropriate testing frameworks
- Consider performance and load testing where relevant"""

    async def execute(self, prompt: str, context: AgentContext) -> AgentResult:
        """Execute testing task."""
        messages = self._build_messages(prompt, context)

        test_prompt = f"""{prompt}

Please provide:
1. **Test Plan**: Overview of testing strategy
2. **Test Cases**: Detailed test cases with:
   - Test ID and description
   - Preconditions
   - Steps to execute
   - Expected results
   - Priority (Critical/High/Medium/Low)
3. **Edge Cases**: Boundary conditions and error scenarios
4. **Test Code**: Actual test implementation (if applicable)

Format test code in appropriate code blocks."""

        messages[-1] = messages[-1].__class__(role="user", content=test_prompt)

        response = await self._llm_complete(messages)

        return AgentResult(
            success=True,
            output=response.content,
            data={
                "test_specification": response.content,
            },
            metrics={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
