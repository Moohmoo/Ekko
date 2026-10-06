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

from agents import classify_articles, generate_briefing
from collectors import fetch_hacker_news_articles, fetch_hugging_face_papers
from config import Settings, get_settings
from models import Article
from notifier import send_system_notification
from providers import create_llm_provider
from storage import (
    get_today_briefing_path,
    is_already_generated,
    load_history,
    normalize_url,
    purge_old_history,
    save_history,
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
    history: dict[str, str],
) -> list[Article]:
    """Élimine les articles déjà présents dans l'historique."""
    unseen: list[Article] = []
    for art in articles:
        canon_url = normalize_url(art.url)
        if canon_url not in history:
            unseen.append(art)
    return unseen


def update_history_with_articles(
    history: dict[str, str],
    articles: list[Article],
) -> None:
    """Enregistre les nouvelles URLs dans l'historique avec la date du jour."""
    today_str = date.today().isoformat()
    for art in articles:
        history[normalize_url(art.url)] = today_str


async def execute_daily_watch(settings: Settings, force: bool = False, custom_date: str | None = None) -> int:
    """Exécute l'intégralité du pipeline de veille de bout en bout."""
    briefing_file = get_today_briefing_path(settings.watch_dir_path, custom_date)
    if is_already_generated(briefing_file) and not force:
        logger.info("Le briefing du jour existe déjà : %s (utiliser --force)", briefing_file)
        return 0

    history = load_history(settings.history_file_path)
    history = purge_old_history(history, settings.history_retention_days)

    candidates = await collect_all_candidates(settings)
    fresh_articles = filter_unseen_articles(candidates, history)
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

    update_history_with_articles(history, fresh_articles)
    save_history(settings.history_file_path, history)

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
