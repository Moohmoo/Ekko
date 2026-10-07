"""Adaptateur (Tool Adapter) reliant le domaine Veille à l'orchestrateur Ekko.

Permet à l'agent d'appeler la veille quotidienne sans dupliquer
ni modifier la logique métier du package watch.
"""

from pathlib import Path
from pydantic import BaseModel, Field

from config import get_settings
from tools.base import BaseTool
from .pipeline import execute_daily_watch
from .storage import get_today_briefing_path, is_already_generated


class WatchToolParams(BaseModel):
    """Paramètres acceptés pour le déclenchement de la veille."""

    force: bool = Field(
        default=False,
        description="Mettre à True pour forcer la regénération même si le briefing d'aujourd'hui existe déjà.",
    )


def _format_briefing_result(briefing_path: Path, prefix: str) -> str:
    """Lit et formate le contenu du briefing pour l'observation de l'agent."""
    if briefing_path.is_file():
        content = briefing_path.read_text(encoding="utf-8").strip()
        return f"{prefix} (`{briefing_path}`) :\n\n{content}"
    return f"{prefix} (`{briefing_path}`), mais le fichier est introuvable."


class WatchTool(BaseTool):
    """Outil permettant à l'agent Ekko de générer le Morning Briefing."""

    name = "run_daily_watch"
    description = (
        "Collecte et synthétise les actualités, news et la veille tech/IA du jour "
        "(Hacker News et Hugging Face) sous forme d'un Morning Briefing Markdown."
    )
    parameters_schema = WatchToolParams

    async def execute(self, force: bool = False) -> str:
        """Déclenche le pipeline de veille et retourne le contenu du briefing."""
        settings = get_settings()
        briefing_path = get_today_briefing_path(settings.watch_dir_path)

        if is_already_generated(briefing_path) and not force:
            return _format_briefing_result(briefing_path, "Briefing du jour disponible")

        exit_code = await execute_daily_watch(settings, force=force)
        if exit_code == 0:
            return _format_briefing_result(briefing_path, "Briefing du jour généré avec succès")
        return "Une erreur est survenue lors de l'exécution de la veille."
