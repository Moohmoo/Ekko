"""Adaptateur (Tool Adapter) reliant le domaine Veille à l'orchestrateur Ekko.

Permet à l'agent d'appeler la veille quotidienne sans dupliquer
ni modifier la logique métier du package watch.
"""

from pathlib import Path
from pydantic import BaseModel, Field

from config import get_settings
from tools.base import BaseTool
from .service import get_or_create_daily_briefing
from .storage import get_today_briefing_path


class WatchToolParams(BaseModel):
    """Paramètres acceptés pour le déclenchement de la veille."""

    force: bool = Field(
        default=False,
        description="Mettre à True pour forcer la regénération même si le briefing d'aujourd'hui existe déjà.",
    )
    query: str | None = Field(
        default=None,
        description="Mot-clé ou sujet spécifique à filtrer dans la veille (ex: 'bioinfo', 'llm'). Laisser vide pour tout le briefing.",
    )


def _extract_article_blocks(content: str) -> list[str]:
    """Découpe le contenu Markdown du briefing en blocs d'articles individuels."""
    raw_blocks = content.split("### ")
    return [f"### {b.strip()}" for b in raw_blocks if b.strip()]


def _filter_articles(blocks: list[str], query: str) -> str:
    """Filtre les articles par mot-clé ou liste les sujets disponibles en cas d'absence."""
    q = query.strip().lower()
    matches = [b for b in blocks if q in b.lower()]
    if matches:
        return f"Articles correspondant à '{query}' :\n\n" + "\n\n".join(matches)

    titles = [b.split("\n")[0].replace("### ", "").strip() for b in blocks]
    summary = "\n".join(f"- {t}" for t in titles)
    return (
        f"Aucun article ne correspond à '{query}' dans la veille d'aujourd'hui.\n"
        f"Sujets et titres disponibles :\n{summary}"
    )


def _format_briefing_result(content: str, label: str, query: str | None = None) -> str:
    """Formate le contenu du briefing pour l'observation de l'agent."""
    if query and query.strip():
        blocks = _extract_article_blocks(content)
        return _filter_articles(blocks, query)
    return f"{label} :\n\n{content}"


class WatchTool(BaseTool):
    """Outil permettant à l'agent Ekko de consulter ou générer la veille."""

    name = "run_daily_watch"
    description = (
        "Consulte ou génère la veille technologique et scientifique du jour. "
        "Permet de récupérer l'ensemble du briefing ou de filtrer par thématique via 'query'."
    )
    parameters_schema = WatchToolParams

    async def execute(self, force: bool = False, query: str | None = None) -> str:
        """Déclenche ou consulte la veille avec filtrage thématique optionnel."""
        settings = get_settings()
        briefing_path = get_today_briefing_path(settings.watch_dir_path)
        try:
            content, is_new = await get_or_create_daily_briefing(settings, force=force)
            status_text = "Briefing généré avec succès" if is_new else "Briefing du jour disponible"
            label = f"{status_text} (`{briefing_path}`)"
            return _format_briefing_result(content, label, query)
        except Exception as exc:
            return f"Une erreur est survenue lors de l'exécution de la veille : {exc}"
