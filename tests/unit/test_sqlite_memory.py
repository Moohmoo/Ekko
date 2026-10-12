"""Unit tests for the SQLite persistent memory adapter."""

from pathlib import Path
import pytest

from ekko.core.models import Message, ToolCall
from ekko.core.ports import MemoryPort
from ekko.memory.sqlite_memory import SqliteMemory


def test_sqlite_memory_satisfies_memory_port(tmp_path: Path) -> None:
    """Ensure SqliteMemory complies with MemoryPort Protocol."""
    mem = SqliteMemory(db_path=tmp_path / "test.db")
    assert isinstance(mem, MemoryPort)


@pytest.mark.asyncio
async def test_sqlite_memory_add_and_get_messages(tmp_path: Path) -> None:
    """Ensure simple messages are stored and retrieved chronologically."""
    mem = SqliteMemory(db_path=tmp_path / "test.db")
    session_id = "sess_1"

    await mem.add_message(session_id, Message(role="user", content="Hello"))
    await mem.add_message(session_id, Message(role="assistant", content="Hi there"))

    history = await mem.get_messages(session_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == "Hello"
    assert history[1].role == "assistant"
    assert history[1].content == "Hi there"


@pytest.mark.asyncio
async def test_sqlite_memory_tool_calls_and_results(tmp_path: Path) -> None:
    """Ensure messages with tool calls and role='tool' are serialized and restored faithfully."""
    mem = SqliteMemory(db_path=tmp_path / "test.db")
    session_id = "sess_tool"

    call = ToolCall(id="call_99", name="calculator", arguments={"a": 1, "b": 2})
    asst_msg = Message(role="assistant", content=None, tool_calls=[call])
    tool_msg = Message(role="tool", content="3", tool_call_id="call_99")

    await mem.add_message(session_id, asst_msg)
    await mem.add_message(session_id, tool_msg)

    history = await mem.get_messages(session_id)
    assert len(history) == 2
    assert history[0].role == "assistant"
    assert history[0].content == ""
    assert len(history[0].tool_calls) == 1
    assert history[0].tool_calls[0].name == "calculator"
    assert history[0].tool_calls[0].arguments == {"a": 1, "b": 2}
    assert history[1].role == "tool"
    assert history[1].content == "3"
    assert history[1].tool_call_id == "call_99"


@pytest.mark.asyncio
async def test_sqlite_memory_bounded_limit(tmp_path: Path) -> None:
    """Ensure get_messages limit returns only the last N chronological messages."""
    mem = SqliteMemory(db_path=tmp_path / "test.db")
    session_id = "sess_limit"

    for i in range(1, 6):
        await mem.add_message(session_id, Message(role="user", content=f"Message {i}"))

    # Request limit of 3 messages (should be messages 3, 4, 5)
    recent = await mem.get_messages(session_id, limit=3)
    assert len(recent) == 3
    assert recent[0].content == "Message 3"
    assert recent[1].content == "Message 4"
    assert recent[2].content == "Message 5"


@pytest.mark.asyncio
async def test_sqlite_memory_session_isolation(tmp_path: Path) -> None:
    """Ensure sessions do not leak into each other."""
    mem = SqliteMemory(db_path=tmp_path / "test.db")
    await mem.add_message("a", Message(role="user", content="From A"))
    await mem.add_message("b", Message(role="user", content="From B"))

    msgs_a = await mem.get_messages("a")
    msgs_b = await mem.get_messages("b")

    assert len(msgs_a) == 1 and msgs_a[0].content == "From A"
    assert len(msgs_b) == 1 and msgs_b[0].content == "From B"


@pytest.mark.asyncio
async def test_sqlite_memory_clear_session(tmp_path: Path) -> None:
    """Ensure clearing a session deletes only its messages."""
    mem = SqliteMemory(db_path=tmp_path / "test.db")
    await mem.add_message("to_clear", Message(role="user", content="Temp"))
    await mem.add_message("to_keep", Message(role="user", content="Keep"))

    await mem.clear_session("to_clear")

    assert await mem.get_messages("to_clear") == []
    assert len(await mem.get_messages("to_keep")) == 1


@pytest.mark.asyncio
async def test_sqlite_memory_persistence_across_instances(tmp_path: Path) -> None:
    """Ensure data persists when a new adapter instance connects to the same database file."""
    db_file = tmp_path / "persistent.db"

    # Process/instance 1 writes conversation
    mem1 = SqliteMemory(db_path=db_file)
    await mem1.add_message("session_x", Message(role="user", content="Turn 1 from run 1"))
    await mem1.add_message("session_x", Message(role="assistant", content="Reply 1 from run 1"))
    del mem1

    # Process/instance 2 opens the database file and resumes
    mem2 = SqliteMemory(db_path=db_file)
    history = await mem2.get_messages("session_x")
    assert len(history) == 2
    assert history[0].content == "Turn 1 from run 1"
    assert history[1].content == "Reply 1 from run 1"

    # Add further turns with mem2
    await mem2.add_message("session_x", Message(role="user", content="Turn 2 from run 2"))
    updated_history = await mem2.get_messages("session_x")
    assert len(updated_history) == 3
    assert updated_history[2].content == "Turn 2 from run 2"


@pytest.mark.asyncio
async def test_sqlite_memory_concurrent_access(tmp_path: Path) -> None:
    """Ensure concurrent writes across instances and sessions succeed without locking."""
    import asyncio

    db_file = tmp_path / "concurrent.db"
    mem_a = SqliteMemory(db_path=db_file)
    mem_b = SqliteMemory(db_path=db_file)

    async def write_turns(mem: SqliteMemory, session_id: str, count: int) -> None:
        for idx in range(count):
            await mem.add_message(session_id, Message(role="user", content=f"msg_{idx}"))

    # Concurrently write 20 messages each to different sessions
    await asyncio.gather(
        write_turns(mem_a, "sess_alpha", 20),
        write_turns(mem_b, "sess_beta", 20),
    )

    history_a = await mem_a.get_messages("sess_alpha", limit=100)
    history_b = await mem_b.get_messages("sess_beta", limit=100)
    assert len(history_a) == 20
    assert len(history_b) == 20


def test_sqlite_memory_connection_closure_guaranteed(tmp_path: Path) -> None:
    """Ensure SqliteMemory._connection context manager closes connection on exit."""
    mem = SqliteMemory(db_path=tmp_path / "leak_test.db")
    captured_conn = None
    with mem._connection() as conn:
        captured_conn = conn
        assert conn.total_changes is not None

    with pytest.raises(Exception):
        captured_conn.execute("SELECT 1;")



@pytest.mark.asyncio
async def test_sqlite_memory_react_sequence_integrity_preserved(tmp_path: Path) -> None:
    """Ensure rolling window does not orphan a tool message by including its caller assistant message."""
    from ekko.core.models import ToolCall

    mem = SqliteMemory(db_path=tmp_path / "react_window.db")
    session = "react_sess"

    tcall = ToolCall(id="call_x", name="calc", arguments={"v": 42})
    await mem.add_message(session, Message(role="user", content="Turn 1"))
    await mem.add_message(session, Message(role="assistant", tool_calls=[tcall]))
    await mem.add_message(session, Message(role="tool", content="42", tool_call_id="call_x"))
    await mem.add_message(session, Message(role="assistant", content="Result is 42"))
    await mem.add_message(session, Message(role="user", content="Turn 2"))
    await mem.add_message(session, Message(role="assistant", content="Reply 2"))

    # Total 6 messages. If we ask for limit=4, normal limit would take:
    # [Tool, Assistant(Result), User(Turn 2), Assistant(Reply 2)]
    # With ReAct integrity, it MUST pull in Assistant(tool_calls=[tcall])
    window_msgs = await mem.get_messages(session, limit=4)
    assert len(window_msgs) == 5
    assert window_msgs[0].role == "assistant"
    assert len(window_msgs[0].tool_calls) == 1
    assert window_msgs[1].role == "tool"
    assert window_msgs[1].tool_call_id == "call_x"

