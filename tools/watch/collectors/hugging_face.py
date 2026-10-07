"""Collecteur asynchrone pour les Daily Papers de Hugging Face.

Récupère les articles scientifiques populaires du jour publiés sur Hugging Face
et les formate selon le modèle Article standard.
"""

from typing import Any
import httpx

from core import Logger
from ..schemas import Article

logger = Logger("ekko.watch.collectors.hf")

HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def format_hf_summary(paper_data: dict[str, Any], raw_summary: str) -> str:
    """Produit un résumé compact avec les upvotes et le début de l'abstract."""
    upvotes = paper_data.get("upvotes", 0)
    cleaned_abstract = raw_summary.replace("\n", " ").strip()
    truncated_abstract = cleaned_abstract[:250] + ("..." if len(cleaned_abstract) > 250 else "")
    return f"HF Upvotes: {upvotes} | Abstract: {truncated_abstract}"


def parse_hf_paper(item: dict[str, Any]) -> Article | None:
    """Convertit un élément brut de l'API Hugging Face en modèle Article."""
    paper = item.get("paper", {})
    paper_id = paper.get("id")
    title = item.get("title") or paper.get("title")
    if not paper_id or not title:
        return None

    raw_summary = item.get("summary") or paper.get("summary") or ""
    summary = format_hf_summary(paper, raw_summary)
    url = f"https://huggingface.co/papers/{paper_id}"
    return Article(
        title=title.strip(),
        url=url,
        summary=summary,
        source_name="Hugging Face Daily Papers",
    )


async def fetch_hugging_face_papers(top_limit: int = 10) -> list[Article]:
    """Interroge l'API Hugging Face et extrait les N papiers les plus populaires."""
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(HF_DAILY_PAPERS_URL, timeout=10.0)
            res.raise_for_status()
            raw_papers: list[dict[str, Any]] = res.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("Impossible de récupérer les papers Hugging Face : %s", exc)
            return []

    articles: list[Article] = []
    for item in raw_papers:
        parsed = parse_hf_paper(item)
        if parsed:
            articles.append(parsed)
        if len(articles) >= top_limit:
            break
    return articles
