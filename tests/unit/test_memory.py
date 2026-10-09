"""Unit tests for the memory port and in-memory session adapter."""

import pytest

from ekko.core.models import Message
from ekko.core.ports import MemoryPort
from ekko.memory.in_memory import InMemoryMemory


def test_in_memory_implements_memory_port() -> None:
    """Ensure InMemoryMemory satisfies the domain MemoryPort protocol."""
    mem = InMemoryMemory()
    assert isinstance(mem, MemoryPort)


@pytest.mark.asyncio
async def test_in_memory_add_and_retrieve_messages() -> None:
    """Ensure messages are stored and retrieved sequentially per session."""
    mem = InMemoryMemory()
    session_id = "test-session"

    msg1 = Message(role="user", content="Hello")
    msg2 = Message(role="assistant", content="Hi")

    await mem.add_message(session_id, msg1)
    await mem.add_message(session_id, msg2)

    history = await mem.get_messages(session_id)
    assert len(history) == 2
    assert history[0].content == "Hello"
    assert history[1].content == "Hi"


@pytest.mark.asyncio
async def test_in_memory_session_isolation() -> None:
    """Ensure different session IDs do not leak messages into each other."""
    mem = InMemoryMemory()
    await mem.add_message("session-a", Message(role="user", content="Msg A"))
    await mem.add_message("session-b", Message(role="user", content="Msg B"))

    history_a = await mem.get_messages("session-a")
    history_b = await mem.get_messages("session-b")

    assert len(history_a) == 1
    assert history_a[0].content == "Msg A"
    assert len(history_b) == 1
    assert history_b[0].content == "Msg B"


@pytest.mark.asyncio
async def test_in_memory_clear_session() -> None:
    """Ensure clearing a session wipes only its recorded turns."""
    mem = InMemoryMemory()
    await mem.add_message("session-1", Message(role="user", content="To be deleted"))
    await mem.clear_session("session-1")

    history = await mem.get_messages("session-1")
    assert history == []
