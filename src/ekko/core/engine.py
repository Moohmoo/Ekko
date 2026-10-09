"""Core orchestrator executing conversational turns and ReAct tool calling."""

from typing import Any
from ekko.core.models import Message, ToolCall, ToolResult
from ekko.core.ports import LLMProviderPort, MemoryPort
from ekko.utils.logger import get_logger

logger = get_logger("core.engine")

DEFAULT_SYSTEM_PROMPT = (
    "You are Ekko, a modular agentic OS assistant. Be precise, helpful, and concise."
)


def _validate_user_input(text: str) -> str:
    """Validate and sanitize user input before passing down the pipeline."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("User input cannot be empty")
    return cleaned


async def _execute_tool_call(tools: Any, call: ToolCall) -> ToolResult:
    """Execute a single tool call through registry or fallback to error result."""
    if tools is not None:
        tool = tools.get(call.name)
        if tool is not None:
            return await tool.execute(**call.arguments)
    return ToolResult(
        content=f"Tool '{call.name}' not found",
        success=False,
        error="ToolNotFound",
    )


class EkkoEngine:
    """Central orchestrator managing conversation turns, memory, and tool execution."""

    def __init__(
        self,
        provider: LLMProviderPort,
        memory: MemoryPort,
        tools: Any = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_iterations: int = 5,
    ) -> None:
        self.provider = provider
        self.memory = memory
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    async def _run_tool_steps(self, session_id: str, tool_calls: list[ToolCall]) -> None:
        """Execute multiple tool calls sequentially and persist observations."""
        for call in tool_calls:
            logger.debug("Executing tool call '%s' (id=%s)", call.name, call.id)
            result = await _execute_tool_call(self.tools, call)
            msg = Message(role="tool", content=result.content, tool_call_id=call.id)
            await self.memory.add_message(session_id, msg)

    async def process_message(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> str:
        """Run iterative ReAct conversation loop until final reply or ceiling."""
        sanitized = _validate_user_input(user_input)
        logger.info("Starting message turn for session '%s'", session_id)
        await self.memory.add_message(session_id, Message(role="user", content=sanitized))
        tool_schemas = self.tools.get_schemas() if self.tools else None

        for iteration in range(self.max_iterations):
            logger.debug("ReAct loop step %d/%d", iteration + 1, self.max_iterations)
            history = await self.memory.get_messages(session_id)
            payload = [Message(role="system", content=self.system_prompt), *history]
            response = await self.provider.generate(payload, tools=tool_schemas)

            if not response.tool_calls:
                asst_msg = Message(role="assistant", content=response.content)
                await self.memory.add_message(session_id, asst_msg)
                logger.info("Completed message turn for session '%s' in %d step(s)", session_id, iteration + 1)
                return response.content

            asst_call_msg = Message(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            )
            await self.memory.add_message(session_id, asst_call_msg)
            await self._run_tool_steps(session_id, response.tool_calls)

        logger.warning("Hit max_iterations (%d) without final answer for session '%s'", self.max_iterations, session_id)
        return "Max iterations reached without final response."

