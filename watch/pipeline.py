"""Point d'entrée principal pour le système de veille automatisé Ekko.

Coordonne les collecteurs, la persistance locale anti-doublon,
les agents IA (Trieur et Rédacteur) et la notification système Ubuntu.
"""

import argparse
import asyncio
from datetime import date
import logging
from pathlib import Path
import sys

from config import Settings, get_settings
from providers import create_llm_provider
from watch.agents import classify_articles, generate_briefing
from watch.collectors import fetch_hacker_news_articles, fetch_hugging_face_papers
from watch.models import Article
from watch.notifier import send_system_notification
from watch.storage import (
    get_today_briefing_path,
    is_already_generated,
    load_seen_urls,
    migrate_json_history_if_exists,
    normalize_url,
    purge_old_urls,
    save_seen_urls,
    write_briefing,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ekko")


def parse_cli_args() -> argparse.Namespace:
    """Analyse les arguments passés en ligne de commande."""
    parser = argparse.ArgumentParser(description="Ekko - Morning Briefing automatisé")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force la regénération du briefing même si le fichier du jour existe déjà",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date cible au format YYYY-MM-DD (par défaut: date du jour)",
    )
    return parser.parse_args()


async def collect_all_candidates(settings: Settings) -> list[Article]:
    """Collecte simultanément les articles depuis Hacker News et Hugging Face."""
    logger.info("Démarrage de la collecte sur Hacker News et Hugging Face...")
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


def filter_unseen_articles(
    articles: list[Article],
    seen_urls: set[str] | dict[str, str],
) -> list[Article]:
    """Élimine les articles déjà répertoriés dans la base de données."""
    unseen: list[Article] = []
    for art in articles:
        canon_url = normalize_url(art.url)
        if canon_url not in seen_urls:
            unseen.append(art)
    return unseen


async def execute_daily_watch(settings: Settings, force: bool = False, custom_date: str | None = None) -> int:
    """Exécute l'intégralité du pipeline de veille de bout en bout."""
    briefing_file = get_today_briefing_path(settings.watch_dir_path, custom_date)
    if is_already_generated(briefing_file) and not force:
        logger.info("Le briefing du jour existe déjà : %s (utiliser --force)", briefing_file)
        return 0

    migrate_json_history_if_exists(settings.history_file_path, settings.db_path)
    purge_old_urls(settings.db_path, settings.history_retention_days)
    seen_urls = load_seen_urls(settings.db_path)

    candidates = await collect_all_candidates(settings)
    fresh_articles = filter_unseen_articles(candidates, seen_urls)
    logger.info("Articles collectés : %d | Nouveaux articles : %d", len(candidates), len(fresh_articles))

    if not fresh_articles:
        logger.info("Aucun nouvel article à traiter. Historique à jour.")
        return 0

    try:
        provider = create_llm_provider(settings)
    except ValueError as exc:
        logger.error("Configuration LLM invalide : %s", exc)
        logger.error("Veuillez renseigner votre GEMINI_API_KEY dans le fichier .env (voir .env.example)")
        return 1

    logger.info("Agent 1 (Trieur) : filtrage et sélection en cours...")
    selection = await classify_articles(fresh_articles, provider)
    logger.info("Articles retenus par le trieur : %d", len(selection.articles))

    logger.info("Agent 2 (Rédacteur) : rédaction du briefing...")
    briefing_md = await generate_briefing(selection, fresh_articles, provider)

    write_briefing(briefing_file, briefing_md)
    logger.info("Briefing écrit avec succès : %s", briefing_file)

    save_seen_urls(settings.db_path, [art.url for art in fresh_articles])

    send_system_notification()
    return 0


def main() -> None:
    """Fonction principale d'exécution synchrone."""
    args = parse_cli_args()
    settings = get_settings()
    exit_code = asyncio.run(execute_daily_watch(settings, force=args.force, custom_date=args.date))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
