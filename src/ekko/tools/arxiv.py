"""ArxivTool querying the arXiv scientific preprints API using Atom XML."""

import xml.etree.ElementTree as ET
import httpx
from pydantic import BaseModel, Field

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool
from ekko.utils.logger import get_logger

logger = get_logger("tools.arxiv")

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
USER_AGENT = "EkkoAgent/1.0 (https://github.com/ekko-org/ekko; mailto:contact@ekko.local)"


class ArxivInput(BaseModel):
    """Input parameters for querying arXiv preprints."""

    query: str | None = Field(
        default=None,
        description=(
            "Mots-clés en anglais ou sujet précis de recherche "
            "(ex: 'diffusion models', 'CRISPR sequence design', 'graph neural network')."
        ),
    )
    categories: list[str] = Field(
        default_factory=lambda: ["cs.AI", "cs.LG", "q-bio.QM", "q-bio.GN", "q-bio.BM"],
        description=(
            "Catégories de recherche arXiv ciblées (ex: 'cs.AI', 'cs.LG', 'q-bio.QM', 'q-bio.GN', 'q-bio.BM')."
        ),
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Nombre maximum de prépublications à renvoyer (1 à 10, défaut 5).",
    )


def _build_search_query(query: str | None, categories: list[str]) -> str:
    """Build compliant arXiv search_query syntax combining categories and individual keywords."""
    parts: list[str] = []
    if categories:
        cat_filter = " OR ".join(f"cat:{c.strip()}" for c in categories if c.strip())
        if cat_filter:
            parts.append(f"({cat_filter})")

    if query and query.strip():
        words = [w.strip() for w in query.strip().split() if w.strip()]
        if words:
            query_filter = " AND ".join(f"all:{w}" for w in words)
            parts.append(f"({query_filter})" if len(words) > 1 else query_filter)

    return " AND ".join(parts) if parts else "all:*"


def _format_authors(authors: list[str]) -> str:
    """Condense author list to top 3 and append 'et al.' if more."""
    if not authors:
        return "Auteurs inconnus"
    if len(authors) <= 3:
        return ", ".join(authors)
    return f"{', '.join(authors[:3])} et al."


def _parse_atom_feed(xml_text: str) -> str:
    """Parse Atom XML feed from arXiv and format readable Markdown summary."""
    root = ET.fromstring(xml_text)
    entries = root.findall("atom:entry", ATOM_NS)
    if not entries:
        return "Aucune prépublication récente trouvée sur arXiv pour ces critères."

    formatted_entries: list[str] = []
    for entry in entries:
        title_el = entry.find("atom:title", ATOM_NS)
        title = " ".join(title_el.text.split()) if title_el is not None and title_el.text else "Sans titre"

        published_el = entry.find("atom:published", ATOM_NS)
        date = published_el.text[:10] if published_el is not None and published_el.text else "Date inconnue"

        id_el = entry.find("atom:id", ATOM_NS)
        link = id_el.text.strip() if id_el is not None and id_el.text else ""

        authors = [
            a.find("atom:name", ATOM_NS).text.strip()
            for a in entry.findall("atom:author", ATOM_NS)
            if a.find("atom:name", ATOM_NS) is not None and a.find("atom:name", ATOM_NS).text
        ]
        authors_str = _format_authors(authors)

        summary_el = entry.find("atom:summary", ATOM_NS)
        summary = " ".join(summary_el.text.split()) if summary_el is not None and summary_el.text else ""
        if len(summary) > 700:
            summary = summary[:700] + "..."

        entry_md = (
            f"### {title}\n"
            f"- **Auteurs** : {authors_str}\n"
            f"- **Date** : {date}\n"
            f"- **Lien** : {link}\n"
            f"- **Résumé** : {summary}"
        )
        formatted_entries.append(entry_md)

    return "\n\n---\n\n".join(formatted_entries)


class ArxivTool(BaseTool):
    """Query recent research preprints from arXiv API."""

    name: str = "arxiv"
    description: str = (
        "Recherche et extrait les dernières prépublications scientifiques sur arXiv "
        "en intelligence artificielle et bio-informatique (IA, apprentissage, biologie computationnelle)."
    )
    args_schema: type[BaseModel] = ArxivInput

    async def _run(
        self,
        query: str | None = None,
        categories: list[str] | None = None,
        limit: int = 5,
    ) -> ToolResult:
        """Execute preprint search on arXiv API with robust error handling."""
        cats = categories if categories is not None else ["cs.AI", "cs.LG", "q-bio.QM", "q-bio.GN", "q-bio.BM"]
        search_query = _build_search_query(query, cats)

        params = {
            "search_query": search_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    ARXIV_API_URL,
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                feed_text = response.text
        except httpx.HTTPStatusError as exc:
            logger.warning("Arxiv API HTTP status error: %s", exc)
            return ToolResult(
                content=f"Erreur HTTP {exc.response.status_code} lors de l'appel à l'API arXiv.",
                success=False,
                error="ArxivHttpError",
            )
        except httpx.RequestError as exc:
            logger.warning("Arxiv API network error: %s", exc)
            return ToolResult(
                content=f"L'API arXiv est inaccessible ou a expiré ({type(exc).__name__}).",
                success=False,
                error="ArxivNetworkError",
            )

        try:
            content = _parse_atom_feed(feed_text)
            return ToolResult(content=content, success=True)
        except ET.ParseError as exc:
            logger.error("Failed to parse arXiv Atom XML payload: %s", exc)
            return ToolResult(
                content="Impossible d'analyser la réponse XML renvoyée par arXiv.",
                success=False,
                error="ArxivParseError",
            )
