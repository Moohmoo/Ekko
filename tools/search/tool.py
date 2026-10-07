"""Outil de recherche web généraliste pour l'agent Ekko.

Interroge DuckDuckGo de manière anonyme et asynchrone sans clé d'API,
restituant les titres, extraits et URLs des résultats pertinents.
"""

import asyncio
from typing import Any
from ddgs import DDGS
from pydantic import BaseModel, Field
from config import get_region_for_language, get_settings
from tools.base import BaseTool


class WebSearchParams(BaseModel):
    """Paramètres pour la requête de recherche web."""

    query: str = Field(
        description="Mots-clés ou question à rechercher sur le web (ex: 'bioinformatique actualités').",
    )
    max_results: int = Field(default=5, description="Nombre maximum de résultats souhaités (1 à 10).")
    region: str | None = Field(
        default=None,
        description="Code région optionnel (ex: 'fr-fr', 'en-us', 'wt-wt'). Si omis, déduit de la langue système.",
    )


def _perform_ddgs_search(query: str, max_results: int, region: str) -> list[dict[str, Any]]:
    """Exécute la recherche DuckDuckGo synchrone dans un thread worker."""
    with DDGS() as client:
        return list(client.text(query.strip(), region=region, max_results=max_results))


def _format_search_results(results: list[dict[str, Any]], query: str) -> str:
    """Met en forme les résultats bruts en Markdown lisible avec liens."""
    if not results:
        return f"Aucun résultat trouvé pour '{query}'."
    blocks: list[str] = [f"Résultats de recherche pour '{query}' :\n"]
    for idx, item in enumerate(results, start=1):
        title = item.get("title", "Sans titre")
        href = item.get("href", "")
        body = item.get("body", "").strip()
        blocks.append(f"{idx}. **[{title}]({href})**\n   {body}")
    return "\n\n".join(blocks)


class WebSearchTool(BaseTool):
    """Outil permettant à l'agent de chercher des informations sur le web."""

    name = "web_search"
    description = (
        "Recherche des informations récentes, actualités, documentations ou articles sur le web. "
        "À utiliser pour toute question d'actualité ou de veille spécifique."
    )
    parameters_schema = WebSearchParams

    async def execute(self, query: str = "", max_results: int = 5, region: str | None = None) -> str:
        """Exécute la recherche de manière asynchrone et formate l'observation."""
        try:
            clean_query = query.strip() or "actualités documentations"
            effective_region = region or get_region_for_language(get_settings().default_language)
            limit = max(1, min(max_results, 10))
            raw_results = await asyncio.to_thread(_perform_ddgs_search, clean_query, limit, effective_region)
            return _format_search_results(raw_results, clean_query)
        except Exception as exc:
            return f"Erreur lors de la recherche web pour '{query}' : {exc}"
