"""Core orchestrator executing conversational turns and ReAct tool calling."""

import json
import time
from collections.abc import AsyncIterator, Mapping
from ekko.core.errors import ProviderError
from ekko.core.events import (
    EngineError,
    EngineEvent,
    StepStarted,
    TokenChunk,
    ToolCallCompleted,
    ToolCallStarted,
    TurnCompleted,
)
from ekko.core.models import Message, ToolCall, ToolResult
from ekko.core.ports import LLMProviderPort, MemoryPort, ToolPort
from ekko.core.prompt import build_default_system_prompt
from ekko.logger import get_logger

logger = get_logger("core.engine")


def _validate_user_input(text: str) -> str:
    """Validate and sanitize user input before passing down the pipeline."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("User input cannot be empty")
    return cleaned


async def _execute_tool_call(tools: Mapping[str, ToolPort] | None, call: ToolCall) -> ToolResult:
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


def _is_streaming_provider(provider: object) -> bool:
    """Determine whether the provider supports explicit real-time streaming."""
    cls = type(provider)
    if hasattr(cls, "generate_stream") and cls.__name__ not in ("AsyncMock", "MagicMock", "Mock"):
        return True
    if "generate_stream" in getattr(provider, "__dict__", {}):
        return True
    return False




def _map_exception_to_engine_error(exc: Exception) -> EngineError:
    """Map infrastructure or execution exceptions to user-actionable EngineError events."""
    if isinstance(exc, ValueError):
        return EngineError(
            error_type="InvalidInput",
            message=str(exc),
            actionable_hint="Veuillez saisir une requête textuelle valide et non vide.",
        )
    if isinstance(exc, ProviderError):
        msg = str(exc)
        hint = (
            "Vérifie qu'Ollama est démarré localement ('systemctl status ollama' ou 'ollama serve') "
            "ou que tes identifiants d'API sont valides."
        )
        return EngineError(
            error_type="ProviderUnavailable",
            message=msg,
            actionable_hint=hint,
        )
    if isinstance(exc, TimeoutError):
        return EngineError(
            error_type="InfrastructureTimeout",
            message=str(exc) or "Upstream request timed out",
            actionable_hint="Le service tiers ou le modèle met trop de temps à répondre. Réessaie dans quelques instants.",
        )
    return EngineError(
        error_type="InternalError",
        message=str(exc),
        actionable_hint="Une erreur imprévue est survenue dans le moteur d'exécution.",
    )


class EkkoEngine:
    """Central orchestrator managing conversation turns, memory, and tool execution."""

    def __init__(
        self,
        provider: LLMProviderPort,
        memory: MemoryPort,
        tools: Mapping[str, ToolPort] | None = None,
        system_prompt: str | None = None,
        max_iterations: int = 5,
        history_limit: int = 10,
        window_size: int = 10,
    ) -> None:
        self.provider = provider
        self.memory = memory
        self.tools = tools
        self.system_prompt = system_prompt if system_prompt is not None else build_default_system_prompt()
        self.max_iterations = max_iterations
        self.window_size = window_size
        self.history_limit = window_size

    async def _run_tool_steps(
        self,
        session_id: str,
        tool_calls: list[ToolCall],
        executed_calls: set[tuple[str, str]],
    ) -> AsyncIterator[EngineEvent]:
        """Execute tool calls sequentially with circuit-breaker and event emission."""
        for call in tool_calls:
            logger.debug("Executing tool call '%s' (id=%s)", call.name, call.id)
            yield ToolCallStarted(
                tool_call_id=call.id,
                tool_name=call.name,
                arguments=call.arguments,
            )

            call_sig = (call.name, json.dumps(call.arguments, sort_keys=True))
            start_time = time.perf_counter()

            if call_sig in executed_calls:
                logger.warning("Duplicate tool call detected in turn for '%s': short-circuiting", call.name)
                result = ToolResult(
                    content="Cet outil a déjà été exécuté avec les mêmes paramètres. Analyse le résultat obtenu et passe à l'étape suivante.",
                    success=False,
                    error="DuplicateToolCall",
                )
            else:
                executed_calls.add(call_sig)
                result = await _execute_tool_call(self.tools, call)

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            yield ToolCallCompleted(
                tool_call_id=call.id,
                tool_name=call.name,
                success=result.success,
                summary=result.content[:200] if result.content else "No output",
                duration_ms=duration_ms,
            )

            content_str = (result.content or "").strip()
            msg_content = content_str if content_str else "(Aucun contenu retourné par l'outil)"
            if not result.success:
                error_label = result.error or "Erreur"
                msg_content = f"[ÉCHEC OUTIL - {error_label}] : {msg_content}"
            msg = Message(role="tool", content=msg_content, tool_call_id=call.id)
            await self.memory.add_message(session_id, msg)



    async def run_stream(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> AsyncIterator[EngineEvent]:
        """Run iterative ReAct conversation loop yielding typed domain events in real-time."""
        try:
            sanitized = _validate_user_input(user_input)
        except Exception as exc:
            yield _map_exception_to_engine_error(exc)
            return

        logger.info("Starting streaming message turn for session '%s'", session_id)
        await self.memory.add_message(session_id, Message(role="user", content=sanitized))
        tool_schemas = self.tools.get_schemas() if self.tools and hasattr(self.tools, "get_schemas") else None
        executed_calls: set[tuple[str, str]] = set()

        for iteration in range(self.max_iterations):
            step_idx = iteration + 1
            logger.debug("ReAct loop step %d/%d", step_idx, self.max_iterations)
            yield StepStarted(step_index=step_idx, max_steps=self.max_iterations)

            history = await self.memory.get_messages(session_id, limit=self.window_size)
            # ReAct integrity guard: never start history payload on an orphan tool response
            while history and history[0].role == "tool":
                history = history[1:]

            if history and history[0].role == "system":
                payload = history
            else:
                payload = [Message(role="system", content=self.system_prompt), *history]


            accumulated_text = ""
            tool_calls: list[ToolCall] = []
            is_streaming = _is_streaming_provider(self.provider)

            buffered_chunks: list[TokenChunk] = []
            try:
                if is_streaming:
                    stream = self.provider.generate_stream(payload, tools=tool_schemas)
                    if hasattr(stream, "__aiter__"):
                        async for item in stream:
                            if isinstance(item, TokenChunk):
                                accumulated_text += item.delta
                                buffered_chunks.append(item)
                            elif isinstance(item, ToolCall):
                                tool_calls.append(item)
                    else:
                        response = await self.provider.generate(payload, tools=tool_schemas)
                        accumulated_text = response.content or ""
                        tool_calls = response.tool_calls
                        is_streaming = False
                else:
                    response = await self.provider.generate(payload, tools=tool_schemas)
                    accumulated_text = response.content or ""
                    tool_calls = response.tool_calls
            except Exception as exc:
                yield _map_exception_to_engine_error(exc)
                return

            if not tool_calls:
                # Direct reply or final synthesis turn: emit accumulated text
                if is_streaming:
                    for chunk in buffered_chunks:
                        yield chunk
                elif accumulated_text:
                    yield TokenChunk(delta=accumulated_text)

                asst_msg = Message(role="assistant", content=accumulated_text)
                await self.memory.add_message(session_id, asst_msg)
                logger.info("Completed message turn for session '%s' in %d step(s)", session_id, step_idx)
                yield TurnCompleted(content=accumulated_text, total_steps=step_idx)
                return

            # Intermediate step calling tools: discard internal narration chunks, record asst call, run tools
            asst_call_msg = Message(
                role="assistant",
                content=accumulated_text or None,
                tool_calls=tool_calls,
            )
            await self.memory.add_message(session_id, asst_call_msg)
            async for event in self._run_tool_steps(session_id, tool_calls, executed_calls):
                yield event

        logger.warning("Hit max_iterations (%d) without final answer for session '%s'", self.max_iterations, session_id)
        yield TurnCompleted(content="Max iterations reached without final response.", total_steps=self.max_iterations)


    async def process_message(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> str:
        """Run iterative ReAct conversation loop until final reply or ceiling (façade over run_stream)."""
        _validate_user_input(user_input)
        async for event in self.run_stream(user_input, session_id=session_id):
            if isinstance(event, TurnCompleted):
                return event.content
            if isinstance(event, EngineError):
                return f"Erreur : {event.message}"
        return "Max iterations reached without final response."



