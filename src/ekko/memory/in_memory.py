"""In-memory session memory adapter fulfilling MemoryPort."""

from collections import defaultdict
from ekko.core.models import Message


class InMemoryMemory:
    """Volatile in-memory store isolating conversations by session id."""

    def __init__(self) -> None:
        self._storage: dict[str, list[Message]] = defaultdict(list)

    async def add_message(self, session_id: str, message: Message) -> None:
        """Append a message to the session message log."""
        self._storage[session_id].append(message)

    async def get_messages(self, session_id: str) -> list[Message]:
        """Return a copy of the recorded conversation turns for session."""
        return list(self._storage[session_id])

    async def clear_session(self, session_id: str) -> None:
        """Reset conversation turns for the specified session."""
        self._storage.pop(session_id, None)
