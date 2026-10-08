"""Outil de recherche universel pour l'agent Ekko (Universal Search).

Combine la recherche scientifique (arXiv), la recherche de code et modèles (GitHub)
et la recherche web générale (DuckDuckGo) via un sélecteur d'angle (focus).
"""

import asyncio
from datetime import datetime
import re
from typing import Literal
import xml.etree.ElementTree as ET
from ddgs import DDGS
import httpx
from pydantic import BaseModel, Field

from config import get_region_for_language, get_settings
from tools.base import BaseTool

USER_AGENT = "Ekko/1.0 (Engineering Assistant; Linux)"


class SearchItem(BaseModel):
    """Représentation structurée d'un résultat de recherche unitaire."""

    title: str = Field(description="Titre du document, article ou dépôt.")
    url: str = Field(description="URL source directe et pérenne.")
    snippet: str = Field(default="", description="Extrait, résumé ou description du contenu.")
    source: str = Field(default="", description="Source ou plateforme d'origine (ex: arXiv, GitHub, Média, Web).")
    date: str = Field(default="", description="Date de publication au format AAAA-MM-JJ ou année.")
    authors: list[str] = Field(default_factory=list, description="Liste des auteurs principaux.")
    stars: int = Field(default=0, description="Nombre d'étoiles GitHub si applicable.")
    language: str = Field(default="", description="Langage principal du dépôt si applicable.")


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


def _build_arxiv_search_query(query: str) -> str:
    """Construit une requête booléenne pour l'API arXiv à partir des termes clés."""
    tokens = [w.strip() for w in query.strip().split() if len(w.strip()) > 1]
    if not tokens:
        return ""
    clean_terms = [t for t in tokens if t.isalnum() or "-" in t]
    target = clean_terms[:5] if clean_terms else tokens[:5]
    return " AND ".join(f"all:{term}" for term in target)


async def _fetch_arxiv_entries(query: str, max_results: int) -> list[SearchItem]:
    """Interroge l'API officielle d'arXiv pour extraire des articles et abstracts récents."""
    search_query = _build_arxiv_search_query(query)
    if not search_query:
        return []
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": search_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": max_results,
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return []
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items: list[SearchItem] = []
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            id_el = entry.find("atom:id", ns)
            pub_el = entry.find("atom:published", ns)
            authors = [a.find("atom:name", ns).text or "" for a in entry.findall("atom:author", ns)]
            items.append(
                SearchItem(
                    title=" ".join((title_el.text or "Sans titre").split()),
                    url=(id_el.text or "").strip(),
                    snippet=" ".join((summary_el.text or "").split()),
                    source="arXiv",
                    date=(pub_el.text or "")[:10],
                    authors=[a for a in authors if a][:3],
                )
            )
        return items
    except Exception:
        return []


async def _fetch_github_repos(query: str, max_results: int) -> list[SearchItem]:
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
                    SearchItem(
                        title=item.get("full_name", ""),
                        url=item.get("html_url", ""),
                        snippet=item.get("description") or "Aucune description",
                        source="GitHub",
                        stars=item.get("stargazers_count", 0),
                        language=item.get("language") or "N/A",
                    )
                    for item in data.get("items", [])[:max_results]
                ]
    except Exception:
        pass
    return []


def _perform_ddgs_web(query: str, max_results: int, region: str) -> list[SearchItem]:
    """Exécute la recherche DuckDuckGo texte de façon synchrone pour le thread worker."""
    try:
        with DDGS() as client:
            hits = list(client.text(query.strip(), region=region, max_results=max_results))
            return [
                SearchItem(
                    title=h.get("title", "Sans titre"),
                    url=h.get("href", ""),
                    snippet=h.get("body", "").strip(),
                    source="Web",
                )
                for h in hits
            ]
    except Exception:
        return []


def _fetch_web_fallback(client: DDGS, query: str, region: str, limit: int) -> list[SearchItem]:
    """Complète la recherche d'actualités avec le web récent pour les sujets techniques."""
    current_year = str(datetime.now().year)
    try:
        hits = list(client.text(f"{query} {current_year}", region=region, max_results=limit))
        return [
            SearchItem(
                title=h.get("title", "Sans titre"),
                url=h.get("href", ""),
                snippet=h.get("body", "").strip(),
                source="Web",
                date=current_year,
            )
            for h in hits
        ]
    except Exception:
        return []


def _perform_ddgs_news(query: str, max_results: int, region: str) -> list[SearchItem]:
    """Exécute la recherche DuckDuckGo News avec repli web si aucun résultat n'est retourné."""
    clean_q = query.strip()
    try:
        with DDGS() as client:
            for limit in ("w", None):
                try:
                    hits = list(client.news(clean_q, region=region, timelimit=limit, max_results=max_results))
                    if len(hits) >= 2:
                        return [
                            SearchItem(
                                title=h.get("title", "Sans titre"),
                                url=h.get("url", ""),
                                snippet=h.get("body", "").strip(),
                                source=h.get("source", "Média"),
                                date=(h.get("date") or "")[:10],
                            )
                            for h in hits
                        ]
                except Exception:
                    pass
            return _fetch_web_fallback(client, clean_q, region, max_results)
    except Exception:
        return []


def _format_academic_results(items: list[SearchItem], query: str) -> str:
    """Met en forme les abstracts scientifiques arXiv pour la restitution à l'agent."""
    if not items:
        return f"Aucun article scientifique trouvé sur arXiv pour '{query}'."
    blocks = [f"Articles scientifiques arXiv pour '{query}' :\n"]
    for idx, item in enumerate(items, start=1):
        authors_str = ", ".join(item.authors) if item.authors else "Auteurs non spécifiés"
        meta = f" - *{authors_str}* ({item.date})" if item.date else f" - *{authors_str}*"
        abstract = item.snippet[:350] + ("..." if len(item.snippet) > 350 else "")
        blocks.append(f"{idx}. **[{item.title}]({item.url})**{meta}\n   {abstract}")
    return "\n\n".join(blocks)


def _format_code_results(items: list[SearchItem], query: str) -> str:
    """Met en forme les dépôts GitHub identifiés avec métadonnées."""
    if not items:
        return f"Aucun dépôt de code trouvé sur GitHub pour '{query}'."
    blocks = [f"Dépôts de code GitHub pour '{query}' :\n"]
    for idx, item in enumerate(items, start=1):
        meta = f" (⭐ {item.stars} | {item.language})"
        blocks.append(f"{idx}. **[{item.title}]({item.url})**{meta}\n   {item.snippet}")
    return "\n\n".join(blocks)


def _format_web_results(items: list[SearchItem], query: str) -> str:
    """Met en forme les résultats de recherche web générale DuckDuckGo."""
    if not items:
        return f"Aucun résultat web trouvé pour '{query}'."
    blocks = [f"Résultats de recherche web pour '{query}' :\n"]
    for idx, item in enumerate(items, start=1):
        blocks.append(f"{idx}. **[{item.title}]({item.url})**\n   {item.snippet}")
    return "\n\n".join(blocks)


def _format_news_results(items: list[SearchItem], query: str) -> str:
    """Met en forme les articles de presse et annonces d'actualité horodatées."""
    if not items:
        return f"Aucun article d'actualité trouvé pour '{query}'."
    blocks = [f"Articles et annonces d'actualité récentes pour '{query}' :\n"]
    for idx, item in enumerate(items, start=1):
        meta = f" ({item.source}, {item.date})" if item.date else f" ({item.source})"
        blocks.append(f"{idx}. **[{item.title}]({item.url})**{meta}\n   {item.snippet}")
    return "\n\n".join(blocks)


def _normalize_item(raw: Any, default_source: str = "") -> SearchItem:
    """Normalise un item brut (dict ou SearchItem) en SearchItem canonique."""
    if isinstance(raw, SearchItem):
        return raw
    if isinstance(raw, dict):
        return SearchItem(
            title=raw.get("title") or raw.get("name") or "Sans titre",
            url=raw.get("url") or raw.get("href") or raw.get("html_url") or "",
            snippet=raw.get("snippet") or raw.get("abstract") or raw.get("description") or raw.get("body") or "",
            source=raw.get("source") or default_source,
            date=str(raw.get("date") or "")[:10],
            authors=raw.get("authors") if isinstance(raw.get("authors"), list) else [],
            stars=int(raw.get("stars", 0)) if str(raw.get("stars", "")).isdigit() else 0,
            language=str(raw.get("language") or ""),
        )
    return SearchItem(title=str(raw), url="")


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

    async def search(
        self,
        query: str = "",
        focus: Literal["academic", "code", "news", "web"] = "news",
        max_results: int = 5,
        region: str | None = None,
    ) -> list[SearchItem]:
        """Effectue la recherche structurée et retourne la liste des items typés."""
        clean_query = query.strip() or "actualités documentations"
        limit = max(1, min(max_results, 10))
        if focus == "academic":
            raw = await _fetch_arxiv_entries(clean_query, limit)
            return [_normalize_item(it, "arXiv") for it in raw]
        if focus == "code":
            raw = await _fetch_github_repos(clean_query, limit)
            return [_normalize_item(it, "GitHub") for it in raw]

        effective_region = region or get_region_for_language(get_settings().default_language)
        if focus == "news":
            raw_news = await asyncio.to_thread(_perform_ddgs_news, clean_query, limit, effective_region)
            return [_normalize_item(it, "Média") for it in raw_news]

        raw_web = await asyncio.to_thread(_perform_ddgs_web, clean_query, limit, effective_region)
        return [_normalize_item(it, "Web") for it in raw_web]

    def format_results(
        self,
        items: list[SearchItem],
        query: str,
        focus: Literal["academic", "code", "news", "web"] = "news",
    ) -> str:
        """Formate une liste d'items typés en observation textuelle pour l'agent."""
        if focus == "academic":
            return _format_academic_results(items, query)
        if focus == "code":
            return _format_code_results(items, query)
        if focus == "news":
            return _format_news_results(items, query)
        return _format_web_results(items, query)

    async def execute(
        self,
        query: str = "",
        focus: Literal["academic", "code", "news", "web"] = "news",
        max_results: int = 5,
        region: str | None = None,
    ) -> str:
        """Exécute la recherche selon le focus sélectionné et formate l'observation."""
        clean_query = query.strip() or "actualités documentations"
        try:
            items = await self.search(
                query=clean_query,
                focus=focus,
                max_results=max_results,
                region=region,
            )
            return self.format_results(items, query=clean_query, focus=focus)
        except Exception as exc:
            return f"Erreur lors de la recherche ({focus}) pour '{query}' : {exc}"
