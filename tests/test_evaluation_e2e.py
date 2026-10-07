"""Tests d'évaluation End-to-End (Evals) paramétrés sur le Golden Dataset.

Charge des scénarios de référence depuis tests/data/golden_evals.json pour vérifier :
- La discrimination fine (rejet du spam, crypto, clickbait et pseudoscience).
- La sensibilité aux pépites (tech SOTA, backend, bioinformatique, vraie cryptographie).
- Le comportement robuste lors de journées à faible volume d'actualités.
"""

import json
from pathlib import Path
from typing import Any
import pytest

from watch.agents import classify_articles
from config import get_settings
from watch.models import Article
from providers import create_llm_provider

DATASET_FILE = Path(__file__).parent / "data" / "golden_evals.json"


def load_scenarios() -> list[dict[str, Any]]:
    """Charge la liste des scénarios d'évaluation depuis le fichier JSON."""
    if not DATASET_FILE.is_file():
        return []
    return json.loads(DATASET_FILE.read_text(encoding="utf-8"))


SCENARIOS = load_scenarios()


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
async def test_classifier_golden_scenarios(scenario: dict[str, Any]) -> None:
    """Exécute l'évaluation de filtrage pour un scénario donné du Golden Dataset."""
    settings = get_settings()
    if not settings.gemini_api_key and settings.llm_provider == "gemini":
        pytest.skip("Test E2E ignoré : aucune clé API Gemini configurée.")

    provider = create_llm_provider(settings)
    articles = [Article.model_validate(raw) for raw in scenario["articles"]]
    result = await classify_articles(articles, provider)

    selected_urls = {art.url for art in result.articles}
    must_drop = set(scenario.get("expected_must_drop", []))
    must_keep = set(scenario.get("expected_must_keep", []))

    # 1. Vérification Anti-Fuite : Aucun bruit ne doit être sélectionné
    leaked = selected_urls & must_drop
    assert not leaked, f"[{scenario['id']}] Bruit non filtré détecté : {leaked}"

    # 2. Vérification Anti-Sur-Filtrage : Les pépites obligatoires sont bien gardées
    missing_gems = must_keep - selected_urls
    assert not missing_gems, f"[{scenario['id']}] Pépites injustement rejetées : {missing_gems}"

    # 3. Volume cible attendu
    min_exp, max_exp = scenario["min_selected"], scenario["max_selected"]
    assert min_exp <= len(result.articles) <= max_exp, (
        f"[{scenario['id']}] Volume {len(result.articles)} hors bornes [{min_exp}, {max_exp}]"
    )
