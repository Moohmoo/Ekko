"""Service métier pour le système de veille automatisé Ekko.

Coordonne la collecte asynchrone, le dédoublonnage d'articles et
les agents IA spécialisés (Trieur et Rédacteur).
"""

import asyncio
from pathlib import Path
from config import Settings
from core import Logger
from agent.memory import SQLiteMemory
from providers import create_llm_provider
from .agents import classify_articles, generate_briefing
from .collectors import fetch_hacker_news_articles, fetch_hugging_face_papers
from .schemas import Article
from .storage import get_today_briefing_path, normalize_url, write_briefing

logger = Logger("ekko.tools.watch")


async def collect_all_candidates(settings: Settings) -> list[Article]:
    """Collecte simultanément les articles depuis Hacker News et Hugging Face."""
    logger.info("Collecte en cours sur Hacker News et Hugging Face...")
    hn_task = fetch_hacker_news_articles(
        top_limit=settings.hn_top_limit,
        min_score=settings.hn_min_score,
    )
    hf_task = fetch_hugging_face_papers(top_limit=settings.hf_top_limit)
    results = await asyncio.gather(hn_task, hf_task, return_exceptions=True)
    articles: list[Article] = []
    for res in results:
        if isinstance(res, list):
            articles.extend(res)
        elif isinstance(res, Exception):
            logger.error("Erreur durant la collecte : %s", res)
    return articles


def filter_unseen_articles(articles: list[Article], seen_urls: set[str]) -> list[Article]:
    """Élimine les articles déjà répertoriés dans la base de données."""
    unseen: list[Article] = []
    for art in articles:
        canon_url = normalize_url(art.url)
        if canon_url not in seen_urls:
            unseen.append(art)
    return unseen


async def get_or_create_daily_briefing(
    settings: Settings,
    force: bool = False,
    custom_date: str | None = None,
) -> tuple[str, bool]:
    """Récupère le briefing du jour s'il existe ou pilote sa génération complète."""
    briefing_file = get_today_briefing_path(settings.watch_dir_path, custom_date)
    if briefing_file.is_file() and not force:
        logger.info("Lecture du briefing existant : %s", briefing_file)
        return briefing_file.read_text(encoding="utf-8").strip(), False

    memory = SQLiteMemory(settings.db_path)
    candidates = await collect_all_candidates(settings)
    fresh_articles = filter_unseen_articles(candidates, memory.get_seen_urls())
    logger.info("Articles candidats : %d | Nouveaux : %d", len(candidates), len(fresh_articles))

    if not fresh_articles:
        logger.info("Aucun nouvel article à traiter. Historique à jour.")
        if briefing_file.is_file():
            return briefing_file.read_text(encoding="utf-8").strip(), False
        return "Aucun nouvel article trouvé pour la veille du jour.", True

    provider = create_llm_provider(settings)
    selection = await classify_articles(fresh_articles, provider)
    briefing_md = await generate_briefing(selection, fresh_articles, provider)

    write_briefing(briefing_file, briefing_md)
    clean_urls = [normalize_url(art.url) for art in fresh_articles]
    memory.record_seen_articles(clean_urls)
    logger.info("Briefing généré et enregistré : %s", briefing_file)

    return briefing_md.strip(), True
