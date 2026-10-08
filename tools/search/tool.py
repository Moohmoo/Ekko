"""Outil de recherche universel pour l'agent Ekko (Universal Search).

Combine la recherche scientifique (arXiv), la recherche de code et modèles (GitHub)
et la recherche web générale (DuckDuckGo) via un sélecteur d'angle (focus).
"""

import asyncio
from typing import Any, Literal
import xml.etree.ElementTree as ET
from ddgs import DDGS
import httpx
from pydantic import BaseModel, Field

from config import get_region_for_language, get_settings
from tools.base import BaseTool

USER_AGENT = "Ekko/1.0 (Engineering Assistant; Linux)"


class SearchParams(BaseModel):
    """Paramètres pour la requête de recherche universelle."""

    query: str = Field(
        description="Mots-clés ou question à rechercher (ex: 'diffusion models protein folding', 'vLLM', 'transformers').",
    )
    focus: Literal["academic", "code", "news", "web"] = Field(
        default="news",
        description="Angle de recherche : 'news' pour les articles de presse et annonces récentes, 'academic' pour les papiers de recherche (arXiv), 'code' pour les dépôts GitHub, 'web' pour les documentations et pages web.",
    )
    max_results: int = Field(default=5, description="Nombre maximum de résultats souhaités (1 à 10).")
    region: str | None = Field(
        default=None,
        description="Code région optionnel pour la recherche web (ex: 'fr-fr', 'en-us').",
    )


# Alias de rétrocompatibilité
WebSearchParams = SearchParams


ARXIV_STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "for", "to", "of", "with", "by", "from",
    "and", "or", "as", "is", "are", "was", "were", "be", "been", "being",
    "recent", "advances", "advance", "advancements", "latest", "new", "novel",
    "research", "studies", "study", "methods", "method", "approach", "approaches",
    "paper", "papers", "survey", "review", "overview",
    "dernier", "derniers", "derniere", "dernieres", "avancees", "avances", "actualites", "progres",
}


def _build_arxiv_search_query(query: str) -> str:
    """Construit une requête booléenne optimisée en ne conservant que les termes pivots."""
    tokens = [w.strip() for w in query.strip().split() if len(w.strip()) > 1]
    filtered = [w for w in tokens if w.lower() not in ARXIV_STOP_WORDS]
    target_words = filtered if filtered else tokens
    return " AND ".join(f"all:{w}" for w in target_words[:4]) if target_words else "all:ai"


async def _fetch_arxiv_entries(query: str, max_results: int) -> list[dict[str, Any]]:
    """Interroge l'API officielle d'arXiv pour extraire des articles et abstracts récents."""
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": _build_arxiv_search_query(query),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": max_results,
    }
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        id_el = entry.find("atom:id", ns)
        pub_el = entry.find("atom:published", ns)
        authors = [a.find("atom:name", ns).text or "" for a in entry.findall("atom:author", ns)]
        results.append({
            "title": " ".join((title_el.text or "Sans titre").split()),
            "abstract": " ".join((summary_el.text or "").split()),
            "url": (id_el.text or "").strip(),
            "date": (pub_el.text or "")[:10],
            "authors": [a for a in authors if a][:3],
        })
    return results


async def _fetch_github_repos(query: str, max_results: int) -> list[dict[str, Any]]:
    """Recherche des dépôts open-source sur l'API publique de GitHub."""
    url = "https://api.github.com/search/repositories"
    params = {"q": query.strip(), "sort": "stars", "order": "desc", "per_page": max_results}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github.v3+json"}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "name": item.get("full_name", ""),
                        "url": item.get("html_url", ""),
                        "description": item.get("description") or "Aucune description",
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language") or "N/A",
                    }
                    for item in data.get("items", [])[:max_results]
                ]
    except Exception:
        pass
    return []


def _perform_ddgs_web(query: str, max_results: int, region: str) -> list[dict[str, Any]]:
    """Exécute la recherche DuckDuckGo texte de façon synchrone pour le thread worker."""
    with DDGS() as client:
        return list(client.text(query.strip(), region=region, max_results=max_results))


def _perform_ddgs_news(query: str, max_results: int, region: str) -> list[dict[str, Any]]:
    """Exécute la recherche DuckDuckGo News d'articles d'actualité récents horodatés."""
    with DDGS() as client:
        try:
            results = list(client.news(query.strip(), region=region, timelimit="w", max_results=max_results))
            return results if results else list(client.news(query.strip(), region=region, max_results=max_results))
        except Exception:
            return list(client.news(query.strip(), region=region, max_results=max_results))


def _format_academic_results(results: list[dict[str, Any]], query: str) -> str:
    """Met en forme les abstracts scientifiques arXiv pour la restitution à l'agent."""
    if not results:
        return f"Aucun article scientifique trouvé sur arXiv pour '{query}'."
    blocks = [f"Articles scientifiques arXiv pour '{query}' :\n"]
    for idx, item in enumerate(results, start=1):
        authors_str = ", ".join(item["authors"]) if item["authors"] else "Auteurs non spécifiés"
        meta = f" - *{authors_str}* ({item['date']})"
        abstract = item["abstract"][:350] + ("..." if len(item["abstract"]) > 350 else "")
        blocks.append(f"{idx}. **[{item['title']}]({item['url']})**{meta}\n   {abstract}")
    return "\n\n".join(blocks)


def _format_code_results(results: list[dict[str, Any]], query: str) -> str:
    """Met en forme les dépôts GitHub identifiés avec métadonnées."""
    if not results:
        return f"Aucun dépôt de code trouvé sur GitHub pour '{query}'."
    blocks = [f"Dépôts de code GitHub pour '{query}' :\n"]
    for idx, item in enumerate(results, start=1):
        meta = f" (⭐ {item['stars']} | {item['language']})"
        blocks.append(f"{idx}. **[{item['name']}]({item['url']})**{meta}\n   {item['description']}")
    return "\n\n".join(blocks)


def _format_web_results(results: list[dict[str, Any]], query: str) -> str:
    """Met en forme les résultats de recherche web générale DuckDuckGo."""
    if not results:
        return f"Aucun résultat web trouvé pour '{query}'."
    blocks = [f"Résultats de recherche web pour '{query}' :\n"]
    for idx, item in enumerate(results, start=1):
        title = item.get("title", "Sans titre")
        href = item.get("href", "")
        body = item.get("body", "").strip()
        blocks.append(f"{idx}. **[{title}]({href})**\n   {body}")
    return "\n\n".join(blocks)


def _format_news_results(results: list[dict[str, Any]], query: str) -> str:
    """Met en forme les articles de presse et annonces d'actualité horodatées."""
    if not results:
        return f"Aucun article d'actualité trouvé pour '{query}'."
    blocks = [f"Articles et annonces d'actualité récentes pour '{query}' :\n"]
    for idx, item in enumerate(results, start=1):
        title = item.get("title", "Sans titre")
        url = item.get("url", "")
        source = item.get("source", "Média")
        date_str = (item.get("date") or "")[:10]
        meta = f" ({source}, {date_str})" if date_str else f" ({source})"
        body = item.get("body", "").strip()
        blocks.append(f"{idx}. **[{title}]({url})**{meta}\n   {body}")
    return "\n\n".join(blocks)


class SearchTool(BaseTool):
    """Outil universel permettant de rechercher sur les actualités, la science, le code ou le web."""

    name = "search"
    description = (
        "Recherche universelle d'informations avec sélecteur 'focus' : "
        "'news' pour les articles de presse et annonces récentes horodatées, "
        "'academic' pour les papiers de recherche et abstracts (arXiv), "
        "'code' pour les dépôts GitHub et modèles SOTA, "
        "'web' pour la documentation générale et pages web."
    )
    parameters_schema = SearchParams

    async def execute(
        self,
        query: str = "",
        focus: Literal["academic", "code", "news", "web"] = "news",
        max_results: int = 5,
        region: str | None = None,
    ) -> str:
        """Exécute la recherche selon le focus sélectionné et formate l'observation."""
        clean_query = query.strip() or "actualités documentations"
        limit = max(1, min(max_results, 10))
        try:
            if focus == "academic":
                results = await _fetch_arxiv_entries(clean_query, limit)
                return _format_academic_results(results, clean_query)
            if focus == "code":
                results = await _fetch_github_repos(clean_query, limit)
                return _format_code_results(results, clean_query)

            effective_region = region or get_region_for_language(get_settings().default_language)
            if focus == "news":
                news_results = await asyncio.to_thread(_perform_ddgs_news, clean_query, limit, effective_region)
                return _format_news_results(news_results, clean_query)

            web_results = await asyncio.to_thread(_perform_ddgs_web, clean_query, limit, effective_region)
            return _format_web_results(web_results, clean_query)
        except Exception as exc:
            return f"Erreur lors de la recherche ({focus}) pour '{query}' : {exc}"


class WebSearchTool(SearchTool):
    """Alias rétrocompatible pour l'ancien nom d'outil web_search."""

    name = "web_search"
