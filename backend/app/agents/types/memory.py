"""
Memory Agent

Manages information retrieval, storage, and organization
for the swarm's collective memory.
"""

from app.agents.base.agent import AgentContext, AgentResult, BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class MemoryAgent(BaseAgent):
    """
    Memory Agent manages information retrieval and storage.
    
    Capabilities:
    - Information retrieval from vector store
    - Knowledge synthesis from multiple sources
    - Memory organization and categorization
    - Context building for other agents
    - Knowledge gap identification
    """

    agent_type = "memory"
    default_system_prompt = """You are an expert AI Memory Agent. Your role is to:

1. Retrieve and synthesize relevant information from memory
2. Organize knowledge in meaningful ways
3. Build comprehensive context for other agents
4. Identify information gaps
5. Maintain the swarm's collective knowledge

When processing information:
- Synthesize multiple sources into coherent summaries
- Identify key concepts and relationships
- Highlight important details vs. noise
- Structure information for easy consumption by other agents
- Flag when information is insufficient or uncertain"""

    async def execute(self, prompt: str, context: AgentContext) -> AgentResult:
        """Execute memory retrieval and synthesis task."""
        # First, retrieve relevant memories
        memories = await self.read_memory(query=prompt, limit=20)

        memory_context = ""
        if memories:
            memory_parts = ["## Retrieved Information:"]
            for i, mem in enumerate(memories, 1):
                memory_parts.append(f"{i}. [{mem.get('memory_type', 'unknown')}] {mem.get('content', '')[:500]}")
            memory_context = "\n".join(memory_parts)

        messages = self._build_messages(prompt, context)

        # Inject retrieved memories into context
        if memory_context:
            messages.insert(1, messages[0].__class__(role="system", content=memory_context))

        memory_prompt = f"""Based on the retrieved information and your knowledge, provide a comprehensive response to:

{prompt}

Synthesize the information, identify key insights, and structure your response clearly.
If the retrieved information is insufficient, clearly state what additional information would be helpful."""

        messages[-1] = messages[-1].__class__(role="user", content=memory_prompt)

        response = await self._llm_complete(messages)

        # Store the synthesis in memory
        await self.write_memory(
            content=f"Query: {prompt}\nSynthesis: {response.content[:1000]}",
            memory_type="semantic",
            metadata={"query": prompt, "synthesized": True},
        )

        return AgentResult(
            success=True,
            output=response.content,
            data={
                "synthesis": response.content,
                "sources_consulted": len(memories),
            },
            metrics={
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "memories_retrieved": len(memories),
            },
        )
