"""
Coding Agent

Generates, reviews, and debugs code. Supports multiple languages
and follows best practices.
"""

import json
from typing import Any, Dict

from app.agents.base.agent import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class CodingAgent(BaseAgent):
    """
    Coding Agent writes, reviews, and debugs code.
    
    Capabilities:
    - Code generation in multiple languages
    - Code review and refactoring
    - Bug fixing and debugging
    - Test generation
    - Documentation generation
    - Architecture suggestions
    """

    agent_type = "coding"
    default_system_prompt = """You are an expert AI Coding Agent. Your role is to:

1. Write clean, efficient, well-documented code
2. Follow best practices and design patterns
3. Consider edge cases and error handling
4. Write modular, testable code
5. Provide clear explanations of your implementation

When generating code:
- Include comments explaining complex logic
- Handle errors gracefully
- Follow language-specific conventions
- Consider performance implications
- Include usage examples where helpful

Supported languages: Python, JavaScript/TypeScript, Go, Rust, Java, C/C++, SQL, HTML/CSS, Shell, and more."""

    async def execute(self, prompt: str, context: AgentContext) -> AgentResult:
        """Execute coding task."""
        messages = self._build_messages(prompt, context)

        coding_prompt = f"""{prompt}

Please provide:
1. **Code Solution**: Complete, production-ready code with comments
2. **Explanation**: How the code works and design decisions
3. **Usage Example**: How to use the code
4. **Edge Cases**: What edge cases are handled
5. **Improvements**: Potential optimizations or enhancements

Format the code solution in a code block with the appropriate language identifier."""

        messages[-1] = messages[-1].__class__(role="user", content=coding_prompt)

        response = await self._llm_complete(messages)

        # Extract code blocks from response
        content = response.content
        code_blocks = []
        artifacts = []

        import re
        code_pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(code_pattern, content, re.DOTALL)
        for lang, code in matches:
            code_blocks.append({
                "language": lang or "text",
                "code": code.strip(),
            })
            artifacts.append({
                "type": "code",
                "language": lang or "text",
                "content": code.strip(),
            })

        return AgentResult(
            success=True,
            output=response.content,
            data={
                "code_blocks": code_blocks,
                "generated_code": "\n\n".join(cb["code"] for cb in code_blocks) if code_blocks else content,
            },
            artifacts=artifacts,
            metrics={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "code_blocks_generated": len(code_blocks),
            },
        )
