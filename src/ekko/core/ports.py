"""Abstract ports (interfaces) defining inbound and outbound domain boundaries."""

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable
from ekko.core.events import TokenChunk
from ekko.core.models import (
    KnowledgeNote,
    Message,
    ModelResponse,
    RawSignal,
    SignalStatus,
    ToolCall,
    ToolResult,
)


@runtime_checkable
class LLMProviderPort(Protocol):
    """Port defining the contract for LLM inference adapters."""

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a response from the underlying LLM provider."""
        ...


@runtime_checkable
class StreamingLLMProviderPort(LLMProviderPort, Protocol):
    """Optional port extending LLMProviderPort with real-time streaming capabilities."""

    async def generate_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[TokenChunk | ToolCall]:
        """Stream normalized response chunks and tool calls from the underlying LLM provider."""
        ...



@runtime_checkable
class MemoryPort(Protocol):
    """Port defining conversation session memory persistence."""

    async def add_message(self, session_id: str, message: Message) -> None:
        """Persist a message into the specified session."""
        ...

    async def get_messages(self, session_id: str, limit: int = 10) -> list[Message]:
        """Retrieve conversation history for the session, up to limit turns."""
        ...

    async def clear_session(self, session_id: str) -> None:
        """Remove all messages associated with the specified session."""
        ...


@runtime_checkable
class ToolPort(Protocol):
    """Port defining the contract for modular tools and capabilities."""

    name: str
    description: str

    def get_schema(self) -> dict[str, Any]:
        """Return the tool JSON schema definition for LLM tool calling."""
        ...

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool logic using provided parameters."""
        ...


@runtime_checkable
class HybridMemoryPort(Protocol):
    """Port defining unified hybrid search and knowledge notes persistence."""

    async def search_notes(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        mode: str = "hybrid",
        limit: int = 5,
    ) -> list[tuple[KnowledgeNote, float]]:
        """Search knowledge notes with hybrid lexical/semantic ranking."""
        ...

    async def get_recent_notes(self, limit: int = 5) -> list[KnowledgeNote]:
        """Retrieve most recent knowledge notes ordered by creation time DESC."""
        ...

    async def get_raw_signals(
        self,
        source_id: str | None = None,
        status: SignalStatus | str | None = None,
        limit: int = 10,
    ) -> list[RawSignal]:
        """Fetch raw signals matching source and status criteria."""
        ...

    async def get_pending_signals(self, limit: int = 5) -> list[RawSignal]:
        """Retrieve un-distilled raw signals in retained status."""
        ...

    async def mark_signal_status(self, signal_id: str, status: SignalStatus | str) -> None:
        """Update the processing status of a raw signal."""
        ...

    async def save_knowledge_note(
        self,
        note: KnowledgeNote,
        embedding: list[float] | None = None,
    ) -> None:
        """Persist a distilled knowledge note with FTS and vector indexing."""
        ...

    async def delete_knowledge_note(self, note_id: str) -> bool:
        """Delete a knowledge note and all associated chunks and indexes."""
        ...

    async def get_popular_tags(self, limit: int = 30) -> list[str]:
        """Fetch most frequently used tags across all knowledge notes."""
        ...



@runtime_checkable
class IngestionPort(Protocol):
    """Port defining asynchronous background ingestion coordination."""

    async def run_once(self) -> dict[str, int]:
        """Execute a single polling pass across all active ingestion sources."""
        ...


@runtime_checkable
class EmbedderPort(Protocol):
    """Port defining local text embedding generation."""

    def embed_query(self, query: str) -> list[float]:
        """Generate dense embedding vector for a single query string."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embedding vectors for a list of strings asynchronously."""
        ...


@runtime_checkable
class ResourceManagerPort(Protocol):
    """Port defining hardware resource management and VRAM lifecycle coordination."""

    def inject_unload_vram(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Inject parameters directing local LLM providers to unload models after inference."""
        ...

