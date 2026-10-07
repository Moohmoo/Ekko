"""Adaptateur (Tool Adapter) reliant le domaine Veille à l'orchestrateur Ekko.

Permet à l'agent d'appeler la veille quotidienne sans dupliquer
ni modifier la logique métier du package watch.
"""

from datetime import date
from pydantic import BaseModel, Field

from config import get_settings
from watch.pipeline import execute_daily_watch
from watch.storage import get_today_briefing_path, is_already_generated
from .base import BaseTool


class WatchToolParams(BaseModel):
    """Paramètres acceptés pour le déclenchement de la veille."""

    force: bool = Field(
        default=False,
        description="Mettre à True pour forcer la regénération même si le briefing d'aujourd'hui existe déjà.",
    )


class WatchTool(BaseTool):
    """Outil permettant à l'agent Ekko de générer le Morning Briefing."""

    name = "run_daily_watch"
    description = (
        "Collecte les actualités tech, IA et sciences du jour (Hacker News et Hugging Face), "
        "élimine les doublons et génère le Morning Briefing Markdown dans data/watch/briefings/."
    )
    parameters_schema = WatchToolParams

    async def execute(self, force: bool = False) -> str:
        """Déclenche le pipeline de veille et retourne un compte-rendu pour le modèle."""
        settings = get_settings()
        briefing_path = get_today_briefing_path(settings.watch_dir_path)

        if is_already_generated(briefing_path) and not force:
            return (
                f"Le briefing du jour ({date.today().isoformat()}) existe déjà dans "
                f"`{briefing_path}`. Spécifiez 'force=True' pour forcer une réactualisation."
            )

        exit_code = await execute_daily_watch(settings, force=force)
        if exit_code == 0:
            return (
                f"Veille quotidienne exécutée avec succès. "
                f"Le briefing Markdown a été rédigé dans `{briefing_path}` "
                f"et une notification système a été émise."
            )
        return "Une erreur est survenue lors de l'exécution de la veille."
