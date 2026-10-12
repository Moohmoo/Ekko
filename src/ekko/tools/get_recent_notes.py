"""GetRecentNotesTool allowing the agent to fetch the most recent distilled notes chronologically."""

from pydantic import BaseModel, Field

from ekko.core.models import KnowledgeNote, ToolResult
from ekko.core.ports import HybridMemoryPort
from ekko.memory.hybrid_store import HybridStore
from ekko.tools.base import BaseTool
from ekko.logger import get_logger

logger = get_logger("tools.get_recent_notes")


class GetRecentNotesInput(BaseModel):
    """Input parameters for fetching recent distilled notes from the vault."""

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of recent notes to retrieve (1 to 20, default 5).",
    )


def _format_note_entry(note: KnowledgeNote) -> str:
    """Format single knowledge note into markdown block."""
    date_str = note.created_at.strftime("%Y-%m-%d %H:%M")
    tags_str = ", ".join(f"#{t}" for t in note.tags) if note.tags else "none"
    sources_str = ", ".join(note.sources) if note.sources else "none"
    preview = note.content.strip().split("\n")[0][:250] if note.content else note.summary

    return (
        f"### {note.title}\n"
        f"- **Date** : {date_str}\n"
        f"- **Tags** : {tags_str}\n"
        f"- **Sources** : {sources_str}\n"
        f"- **Résumé** : {note.summary}\n"
        f"- **Aperçu** : {preview}..."
    )


class GetRecentNotesTool(BaseTool):
    """Tool retrieving the most recent distilled notes from the knowledge vault."""

    name: str = "get_recent_notes"
    description: str = (
        "Retrieve the most recent distilled notes (echoes) from the vault ordered chronologically. "
        "Use this tool when the user asks about recent notes, the latest echo, latest additions, "
        "or recent updates without performing a keyword search."
    )
    args_schema: type[BaseModel] = GetRecentNotesInput

    def __init__(
        self,
        db_manager: HybridMemoryPort | None = None,
        db_path: str = "data/ekko.db",
    ) -> None:
        self.db_manager = db_manager or HybridStore(db_path=db_path)

    async def _run(self, limit: int = 5) -> ToolResult:
        """Fetch latest notes from HybridStore chronologically."""
        logger.debug("Fetching %d most recent notes from vault", limit)
        try:
            notes = await self.db_manager.get_recent_notes(limit=limit)
        except Exception as exc:
            logger.error("Error fetching recent notes: %s", exc)
            return ToolResult(
                content=f"Erreur lors de la récupération des notes récentes : {exc}",
                success=False,
                error="GetRecentNotesError",
            )

        if not notes:
            return ToolResult(
                content="Aucune note distillée trouvée dans le coffre.",
                success=True,
            )

        formatted = [_format_note_entry(n) for n in notes]
        return ToolResult(content="\n\n---\n\n".join(formatted), success=True)
