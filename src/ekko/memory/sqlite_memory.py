"""Local-first SQLite session persistence adapter fulfilling MemoryPort."""

import asyncio
from collections.abc import Generator
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from ekko.core.models import Message, ToolCall
from ekko.logger import get_logger

logger = get_logger("memory.sqlite")

INIT_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
"""

SELECT_MESSAGES_SQL = """
SELECT role, content, tool_call_id, tool_calls_json
FROM (
    SELECT id, role, content, tool_call_id, tool_calls_json
    FROM messages
    WHERE session_id = ?
    ORDER BY id DESC
    LIMIT ?
)
ORDER BY id ASC;
"""


def _serialize_tool_calls(tool_calls: list[ToolCall]) -> str | None:
    """Serialize tool calls list into JSON string for SQLite storage."""
    if not tool_calls:
        return None
    return json.dumps([call.model_dump() for call in tool_calls])


def _deserialize_tool_calls(raw_json: str | None) -> list[ToolCall]:
    """Parse JSON string back into structured ToolCall models."""
    if not raw_json:
        return []
    items = json.loads(raw_json)
    return [ToolCall(**item) for item in items]


class SqliteMemory:
    """Persistent SQLite store ensuring thread-safe local conversation memory."""

    def __init__(self, db_path: str | Path = "data/ekko.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _create_connection(self) -> sqlite3.Connection:
        """Create a connection with busy timeout and WAL mode pragmas."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
        return conn

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager guaranteeing connection closure and transaction commit/rollback."""
        conn = self._create_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize SQLite database schema and WAL mode."""
        with self._connection() as conn:
            conn.executescript(INIT_SQL)

    def _insert_message_sync(self, session_id: str, message: Message) -> None:
        """Insert a message row into the SQLite database synchronously."""
        tool_calls_json = _serialize_tool_calls(message.tool_calls)
        sql = (
            "INSERT INTO messages (session_id, role, content, tool_call_id, tool_calls_json) "
            "VALUES (?, ?, ?, ?, ?)"
        )
        with self._connection() as conn:
            conn.execute(
                sql,
                (session_id, message.role, message.content, message.tool_call_id, tool_calls_json),
            )

    def _query_messages_sync(self, session_id: str, limit: int) -> list[Message]:
        """Fetch chronological messages bounded by limit synchronously."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SELECT_MESSAGES_SQL, (session_id, limit))
            rows = cursor.fetchall()

        messages: list[Message] = []
        for role, content, tool_call_id, tool_calls_json in rows:
            tool_calls = _deserialize_tool_calls(tool_calls_json)
            messages.append(
                Message(
                    role=role,
                    content=content or "",
                    tool_call_id=tool_call_id,
                    tool_calls=tool_calls,
                )
            )
        return messages

    def _delete_session_sync(self, session_id: str) -> None:
        """Remove all messages for a session synchronously."""
        with self._connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))

    async def add_message(self, session_id: str, message: Message) -> None:
        """Persist a message into the specified session asynchronously."""
        await asyncio.to_thread(self._insert_message_sync, session_id, message)

    async def get_messages(self, session_id: str, limit: int = 50) -> list[Message]:
        """Retrieve bounded conversation history in chronological order."""
        return await asyncio.to_thread(self._query_messages_sync, session_id, limit)

    async def clear_session(self, session_id: str) -> None:
        """Remove all messages associated with the specified session."""
        await asyncio.to_thread(self._delete_session_sync, session_id)
