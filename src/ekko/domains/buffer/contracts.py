"""Buffer domain IPC contracts defining retrieval and search payloads."""

from pydantic import BaseModel
from ekko.domains.buffer.entities import KnowledgeNote


class NoteSearchResult(BaseModel):
    """Scored knowledge note returned by hybrid lexical/semantic search."""

    note: KnowledgeNote
    score: float
