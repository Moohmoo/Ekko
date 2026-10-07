"""Collecteur asynchrone pour l'API officielle de Hacker News.

Récupère les meilleures actualités via l'API Firebase REST de Hacker News
et les transforme en modèles d'articles unifiés.
"""

import asyncio
from typing import Any
import httpx

from core import Logger
from ..schemas import Article

logger = Logger("ekko.watch.collectors.hn")

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"


async def fetch_item_data(client: httpx.AsyncClient, item_id: int) -> dict[str, Any] | None:
    """Télécharge les données brutes d'un élément Hacker News spécifique."""
    try:
        response = await client.get(HN_ITEM_URL.format(item_id=item_id), timeout=10.0)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Échec de récupération pour l'item HN %s : %s", item_id, exc)
        return None


def format_hn_summary(item: dict[str, Any]) -> str:
    """Formate une description concise à partir des métadonnées de l'article HN."""
    score = item.get("score", 0)
    comments_count = len(item.get("kids", []))
    summary = f"Score HN: {score} pts | {comments_count} commentaires"
    if item.get("text"):
        summary += f" | {item['text'][:120]}"
    return summary


def parse_hn_article(item: dict[str, Any]) -> Article | None:
    """Convertit un payload brut HN en instance de modèle Article standardisé."""
    title = item.get("title", "").strip()
    item_id = item.get("id")
    if not title or not item_id:
        return None
    raw_url = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
    clean_url = str(raw_url).strip().rstrip("/\\")
    return Article(
        title=title,
        url=clean_url,
        summary=format_hn_summary(item),
        source_name="Hacker News",
    )


async def fetch_hacker_news_articles(
    top_limit: int = 15,
    min_score: int = 50,
) -> list[Article]:
    """Récupère les top articles HN dépassant le score minimum spécifié."""
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(HN_TOP_STORIES_URL, timeout=10.0)
            res.raise_for_status()
            story_ids: list[int] = res.json()[: top_limit * 2]
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("Impossible de joindre l'API top stories HN : %s", exc)
            return []

        tasks = [fetch_item_data(client, sid) for sid in story_ids]
        raw_items = await asyncio.gather(*tasks)

    articles: list[Article] = []
    for raw in raw_items:
        if not raw or raw.get("score", 0) < min_score:
            continue
        parsed = parse_hn_article(raw)
        if parsed:
            articles.append(parsed)
        if len(articles) >= top_limit:
            break
    return articles
