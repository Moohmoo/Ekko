"""Test d'évaluation End-to-End (Evals) du filtrage de l'Agent Trieur.

Évalue la qualité du filtrage sur un Golden Dataset de référence :
- Vérifie qu'aucun bruit (crypto, marketing, micro patch notes, clickbait) ne fuite.
- Vérifie qu'il n'y a pas de sur-filtrage (les pépites tech et bio sont bien conservées).
- Vérifie la conformité du volume (3 à 5 articles retenus).
"""

import pytest
from agents import classify_articles
from config import get_settings
from models import Article
from providers import create_llm_provider

# Jeu de test calibré (4 pépites signal fort + 5 bruits)
GOLDEN_DATASET: list[Article] = [
    # --- PÉPITES (Signal fort à conserver) ---
    Article(
        title="Mistral Large 4: Open-Weights SOTA Foundation Model",
        url="https://ai.example.com/mistral-large-4",
        summary="Mistral AI releases their flagship model outperforming SOTA benchmarks.",
        source_name="Hacker News",
    ),
    Article(
        title="Polars 2.0: Major Rust Engine Rewrite and Distributed Execution",
        url="https://data.example.com/polars-2-release",
        summary="Polars 2.0 introduces distributed execution and 3x faster memory-efficient operations.",
        source_name="Hacker News",
    ),
    Article(
        title="De Novo Protein Generation with Transformer Latents for Oncology Targets",
        url="https://hf.example.com/papers/de-novo-proteins",
        summary="Novel generative transformer designs target-binding proteins validated in-vitro.",
        source_name="Hugging Face Daily Papers",
    ),
    Article(
        title="Zero-Knowledge Proofs for Verifiable ML Inference in Real-Time",
        url="https://backend.example.com/zkml-realtime",
        summary="Algorithmic breakthrough achieves sub-millisecond ZK proofs for transformer inference.",
        source_name="Hacker News",
    ),
    # --- BRUITS (À rejeter catégoriquement) ---
    Article(
        title="Dogecoin surges 35% after meme contest on Twitter",
        url="https://crypto.example.com/doge-pump",
        summary="Speculative trading pumps meme token amidst crypto hype.",
        source_name="Hacker News",
    ),
    Article(
        title="Release v0.4.1: Fixed typo in button margin",
        url="https://github.example.com/minor-css-fix",
        summary="Small bugfix updating CSS margin-top from 4px to 6px.",
        source_name="Hacker News",
    ),
    Article(
        title="10 Unbelievable reasons why AI will fire all software developers by next week!",
        url="https://clickbait.example.com/ai-doom-clickbait",
        summary="Sensationalist speculation with no technical substance.",
        source_name="Hacker News",
    ),
    Article(
        title="Best 5 Cloud Hosting Providers to buy in 2026 (Sponsored)",
        url="https://promo.example.com/best-hosting-deals",
        summary="Affiliate marketing list promoting shared web hosts.",
        source_name="Hacker News",
    ),
    Article(
        title="New NFT drop on Solana features pixel cats",
        url="https://nft.example.com/solana-cats",
        summary="Digital collectibles auction on blockchain.",
        source_name="Hacker News",
    ),
]

NOISE_URLS = {
    "https://crypto.example.com/doge-pump",
    "https://github.example.com/minor-css-fix",
    "https://clickbait.example.com/ai-doom-clickbait",
    "https://promo.example.com/best-hosting-deals",
    "https://nft.example.com/solana-cats",
}

SIGNAL_URLS = {
    "https://ai.example.com/mistral-large-4",
    "https://data.example.com/polars-2-release",
    "https://hf.example.com/papers/de-novo-proteins",
    "https://backend.example.com/zkml-realtime",
}


@pytest.mark.asyncio
async def test_classifier_filtering_quality_and_balance() -> None:
    """Valide que le classifieur rejette tout le bruit sans sur-filtrer les pépites."""
    settings = get_settings()
    if not settings.gemini_api_key and settings.llm_provider == "gemini":
        pytest.skip("Test E2E ignoré en l'absence de clé API configurée.")

    provider = create_llm_provider(settings)
    result = await classify_articles(GOLDEN_DATASET, provider)

    selected_urls = {a.url for a in result.articles}

    # 1. Vérification Anti-Fuite : Zéro bruit ne doit passer
    leaked_noise = selected_urls & NOISE_URLS
    assert not leaked_noise, f"Bruit détecté dans la sélection : {leaked_noise}"

    # 2. Vérification Anti-Sur-Filtrage : Les signaux forts sont bien retenus
    retained_signal = selected_urls & SIGNAL_URLS
    assert len(retained_signal) >= 3, f"Sur-filtrage détecté ! Trop peu de pépites retenues : {len(retained_signal)}"

    # 3. Volume cible : Entre 3 et 5 articles
    assert 3 <= len(result.articles) <= 5, f"Volume hors limites : {len(result.articles)}"
