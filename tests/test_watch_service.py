"""Tests unitaires pour le service de veille (watch service)."""

from pathlib import Path
import pytest
from pydantic import BaseModel
from config import Settings
from agent.memory import SQLiteMemory
from tools.watch.schemas import Article, SelectedArticle, SelectionResult
from tools.watch.service import (
    filter_unseen_articles,
    get_or_create_daily_briefing,
)
from providers.base import LLMProvider


class MockServiceLLM(LLMProvider):
    """Fournisseur LLM simulé pour le service de veille."""

    async def generate_structured(self, prompt: str, schema: type[BaseModel], system_instruction: str = "") -> BaseModel:
        return SelectionResult(
            articles=[SelectedArticle(title="Paper 1", url="https://example.com/p1", category="Tech & IA")]
        )

    async def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        return "### [Tech & IA] Paper 1\n- **C'est quoi :** Nouveau modèle\n- **Pourquoi :** Impact\n- **Source :** [HN](https://example.com/p1)"


def test_filter_unseen_articles() -> None:
    """Vérifie l'exclusion des URLs déjà répertoriées."""
    articles = [
        Article(title="A1", url="https://example.com/1", source_name="HN"),
        Article(title="A2", url="https://example.com/2", source_name="HF"),
    ]
    seen = {"https://example.com/1"}
    filtered = filter_unseen_articles(articles, seen)
    assert len(filtered) == 1
    assert filtered[0].url == "https://example.com/2"


@pytest.mark.asyncio
async def test_get_or_create_daily_briefing_cached(tmp_path: Path) -> None:
    """Vérifie le chargement direct du briefing si déjà existant sur disque."""
    briefing_dir = tmp_path / "briefings"
    briefing_dir.mkdir()
    briefing_file = briefing_dir / "2026-10-07.md"
    briefing_file.write_text("Contenu en cache du briefing", encoding="utf-8")

    settings = Settings(watch_dir_path=briefing_dir, db_path=tmp_path / "test.db")
    content, is_new = await get_or_create_daily_briefing(settings, force=False, custom_date="2026-10-07")

    assert content == "Contenu en cache du briefing"
    assert is_new is False


@pytest.mark.asyncio
async def test_get_or_create_daily_briefing_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie la génération complète quand aucun fichier n'existe."""
    briefing_dir = tmp_path / "briefings"
    db_path = tmp_path / "test.db"
    settings = Settings(watch_dir_path=briefing_dir, db_path=db_path)

    sample_articles = [
        Article(title="Paper 1", url="https://example.com/p1", source_name="HN", summary="Summary 1"),
    ]

    async def mock_collect(_):
        return sample_articles

    monkeypatch.setattr("tools.watch.service.collect_all_candidates", mock_collect)
    monkeypatch.setattr("tools.watch.service.create_llm_provider", lambda _: MockServiceLLM())

    content, is_new = await get_or_create_daily_briefing(settings, force=True, custom_date="2026-10-07")

    assert "Paper 1" in content
    assert is_new is True
    assert (briefing_dir / "2026-10-07.md").is_file()

    # Vérifie que l'URL a bien été persistée dans SQLite
    memory = SQLiteMemory(db_path)
    assert "https://example.com/p1" in memory.get_seen_urls()
