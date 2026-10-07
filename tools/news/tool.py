"""Outil de recherche d'actualités récentes pour l'agent Ekko.

Interroge DuckDuckGo News de manière anonyme et asynchrone sans clé d'API,
restituant les titres, sources, dates de publication, extraits et URLs.
"""

import asyncio
from typing import Any
from ddgs import DDGS
from pydantic import BaseModel, Field
from tools.base import BaseTool


class NewsSearchParams(BaseModel):
    """Parameters for news search requests."""

    query: str = Field(
        description="Mots-clés ou sujet d'actualité recherché (ex: 'bioinformatique', 'intelligence artificielle')."
    )
    max_results: int = Field(default=5, description="Nombre maximum de dépêches souhaitées (1 à 10).")


def _perform_ddgs_news(query: str, max_results: int) -> list[dict[str, Any]]:
    """Execute synchronous DuckDuckGo news search in a thread worker."""
    with DDGS() as client:
        return list(client.news(query.strip(), max_results=max_results))


def _format_news_item(idx: int, item: dict[str, Any]) -> str:
    """Format a single news item with title, source, publication date and body."""
    title = item.get("title", "Sans titre")
    url = item.get("url") or item.get("href", "")
    source = item.get("source", "Source inconnue")
    date_str = item.get("date", "")[:10]
    meta = f" - *{source}*" + (f" ({date_str})" if date_str else "")
    body = item.get("body", "").strip()
    return f"{idx}. **[{title}]({url})**{meta}\n   {body}"


def _format_news_results(results: list[dict[str, Any]], query: str) -> str:
    """Format raw news results into readable Markdown blocks with metadata."""
    if not results:
        return f"Aucune actualité récente trouvée pour '{query}'."
    blocks: list[str] = [f"Actualités récentes pour '{query}' :\n"]
    for idx, item in enumerate(results, start=1):
        blocks.append(_format_news_item(idx, item))
    return "\n\n".join(blocks)


class NewsSearchTool(BaseTool):
    """Tool allowing the agent to retrieve fresh news and press articles."""

    name = "news_search"
    description = (
        "Recherche des actualités récentes et dépêches de presse horodatées sur le web. "
        "À utiliser systématiquement quand l'utilisateur demande des actualités, des news "
        "ou les événements récents sur un sujet."
    )
    parameters_schema = NewsSearchParams

    async def execute(self, query: str, max_results: int = 5) -> str:
        """Execute news search asynchronously and format observation."""
        try:
            limit = max(1, min(max_results, 10))
            raw_results = await asyncio.to_thread(_perform_ddgs_news, query, limit)
            return _format_news_results(raw_results, query)
        except Exception as exc:
            return f"Erreur lors de la recherche d'actualités pour '{query}' : {exc}"
