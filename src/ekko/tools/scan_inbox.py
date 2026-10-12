"""ScanInboxTool allowing the agent to inspect raw unread or pending ingested signals."""

from typing import Literal
from pydantic import BaseModel, Field

from ekko.core.models import RawSignal, SignalStatus, ToolResult
from ekko.core.ports import HybridMemoryPort
from ekko.memory.hybrid_store import HybridStore
from ekko.tools.base import BaseTool
from ekko.logger import get_logger

logger = get_logger("tools.scan_inbox")


class ScanInboxInput(BaseModel):
    """Input parameters for inspecting raw ingested signals in the inbox."""

    status: Literal["pending", "retained", "discarded", "archived"] | None = Field(
        default="pending",
        description="Statut du signal à filtrer ('pending', 'retained', 'discarded', 'archived') ou None pour tout.",
    )
    source_id: str | None = Field(
        default=None,
        description="Identifiant de source pour filtrer (ex: 'hn_tech', 'arxiv_ai').",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Nombre maximum de signaux à afficher (1 à 50, défaut 10).",
    )


def _format_signal_entry(signal: RawSignal) -> str:
    """Format single raw signal into readable markdown block."""
    date_str = signal.ingested_at.strftime("%Y-%m-%d %H:%M")
    author_str = signal.author or "Inconnu"
    url_str = signal.url or "N/A"
    clean_text = (signal.clean_content or signal.raw_content or "").strip()
    preview = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text

    return (
        f"### {signal.title} [{signal.status.value}]\n"
        f"- **Source** : {signal.source_id}\n"
        f"- **Date** : {date_str}\n"
        f"- **Auteur** : {author_str}\n"
        f"- **Lien** : {url_str}\n"
        f"- **Extrait** : {preview}"
    )


class ScanInboxTool(BaseTool):
    """Tool scanning unprocessed raw signals captured by background ingestion connectors."""

    name: str = "scan_inbox"
    description: str = (
        "Consulte la boîte de réception des signaux de veille bruts (raw_signals) "
        "capturés par les connecteurs d'ingestion en arrière-plan."
    )
    args_schema: type[BaseModel] = ScanInboxInput

    def __init__(self, db_manager: HybridMemoryPort | None = None, db_path: str = "data/ekko.db") -> None:
        self.db_manager = db_manager or HybridStore(db_path=db_path)

    async def _run(
        self,
        status: Literal["pending", "retained", "discarded", "archived"] | None = "pending",
        source_id: str | None = None,
        limit: int = 10,
    ) -> ToolResult:
        """Fetch raw signals matching criteria and format into markdown."""
        status_enum = SignalStatus(status) if status else None
        signals = await self.db_manager.get_raw_signals(
            source_id=source_id,
            status=status_enum,
            limit=limit,
        )

        if not signals:
            return ToolResult(
                content="Aucun signal brut trouvé pour ces critères.",
                success=True,
            )

        formatted_entries = [_format_signal_entry(s) for s in signals]
        return ToolResult(content="\n\n---\n\n".join(formatted_entries), success=True)
