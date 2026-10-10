"""QueryKnowledgeTool providing hybrid and lexical/semantic PKM note retrieval."""

import asyncio
from typing import Literal
from pydantic import BaseModel, Field

from ekko.core.models import ToolResult
from ekko.core.ports import HybridMemoryPort
from ekko.memory.embedder import TextEmbedder
from ekko.memory.hybrid_store import HybridStore
from ekko.memory.models import KnowledgeNote
from ekko.tools.base import BaseTool
from ekko.logger import get_logger

logger = get_logger("tools.query_knowledge")


class QueryKnowledgeInput(BaseModel):
    """Input parameters for querying Ekko's local PKM memory."""

    query: str = Field(
        ...,
        description="Mots-clés ou question naturelle pour interroger la base de connaissances.",
    )
    mode: Literal["hybrid", "lexical", "semantic"] = Field(
        default="hybrid",
        description="Mode de recherche : 'hybrid' (FTS5 + vectoriel RRF), 'lexical' (BM25 pur), ou 'semantic' (similarité dense).",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Nombre maximum de notes à renvoyer (1 à 20, défaut 5).",
    )


def _format_note_entry(note: KnowledgeNote, score: float) -> str:
    """Format single knowledge note result into markdown display block."""
    date_str = note.created_at.strftime("%Y-%m-%d")
    tags_str = ", ".join(note.tags) if note.tags else "aucun"
    sources_str = ", ".join(note.sources) if note.sources else "aucune"
    snippet = note.content.strip().split("\n")[0][:250]

    return (
        f"### {note.title} (Score: {score:.4f})\n"
        f"- **Date** : {date_str}\n"
        f"- **Résumé** : {note.summary}\n"
        f"- **Tags** : {tags_str}\n"
        f"- **Sources** : {sources_str}\n"
        f"- **Aperçu** : {snippet}..."
    )


class QueryKnowledgeTool(BaseTool):
    """Tool querying local PKM knowledge notes using FTS5, vector similarity, and RRF fusion."""

    name: str = "query_knowledge"
    description: str = (
        "Recherche dans la base de connaissances et les notes PKM locales d'Ekko "
        "en utilisant la recherche hybride (mots-clés BM25 et similarité sémantique vectorielle)."
    )
    args_schema: type[BaseModel] = QueryKnowledgeInput

    def __init__(
        self,
        db_manager: HybridMemoryPort | None = None,
        embedder: TextEmbedder | None = None,
        db_path: str = "data/ekko.db",
    ) -> None:
        self.db_manager = db_manager or HybridStore(db_path=db_path)
        self.embedder = embedder or TextEmbedder()

    async def _run(
        self,
        query: str,
        mode: Literal["hybrid", "lexical", "semantic"] = "hybrid",
        limit: int = 5,
    ) -> ToolResult:
        """Execute hybrid search against HybridStore and format results."""
        logger.debug("Executing knowledge query '%s' with mode '%s'", query, mode)
        query_vec: list[float] | None = None

        if mode in {"hybrid", "semantic"}:
            query_vec = await asyncio.to_thread(self.embedder.embed_query, query)

        results = await self.db_manager.search_notes(
            query=query,
            query_embedding=query_vec,
            mode=mode,
            limit=limit,
        )

        if not results:
            return ToolResult(
                content=f"Aucune note de connaissance trouvée pour la requête : '{query}'.",
                success=True,
            )

        formatted_entries = [_format_note_entry(note, score) for note, score in results]
        return ToolResult(content="\n\n---\n\n".join(formatted_entries), success=True)
