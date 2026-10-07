"""Tests unitaires pour les agents Classifier et Writer."""

from typing import TypeVar
import pytest
from pydantic import BaseModel

from watch.agents.classifier import classify_articles, validate_selected_articles
from watch.agents.writer import format_selection_context, generate_briefing
from watch.models import Article, SelectedArticle, SelectionResult
from providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Fournisseur LLM simulé pour valider les agents sans requêtes réseau."""

    def __init__(self, structured_return: BaseModel, text_return: str) -> None:
        self.structured_return = structured_return
        self.text_return = text_return

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_instruction: str = "",
    ) -> T:
        return self.structured_return  # type: ignore

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> str:
        return self.text_return


def test_validate_selected_articles_filters_hallucinations() -> None:
    """Vérifie que les URLs non présentes dans les articles d'origine sont filtrées."""
    sources = [
        Article(title="Art 1", url="https://valid.com/1", summary="S1", source_name="HN"),
        Article(title="Art 2", url="https://valid.com/2", summary="S2", source_name="HF"),
    ]
    raw_selection = SelectionResult(
        articles=[
            SelectedArticle(title="Art 1", url="https://valid.com/1", category="Tech & IA"),
            SelectedArticle(title="Faux", url="https://hallucinated.com", category="Tech & IA"),
        ]
    )
    validated = validate_selected_articles(raw_selection, sources)
    assert len(validated.articles) == 1
    assert validated.articles[0].url == "https://valid.com/1"


def test_format_selection_context() -> None:
    """Vérifie l'assemblage du contexte éditorial pour le rédacteur."""
    sources = [Article(title="A1", url="https://a.com", summary="Résumé A", source_name="HN")]
    selection = SelectionResult(
        articles=[SelectedArticle(title="A1", url="https://a.com", category="Data & Backend")]
    )
    context = format_selection_context(selection, sources)
    assert "https://a.com" in context
    assert "Résumé A" in context
    assert "Data & Backend" in context


@pytest.mark.asyncio
async def test_agent_pipeline_with_mock() -> None:
    """Vérifie l'exécution séquentielle des deux agents avec un provider simulé."""
    sources = [Article(title="A1", url="https://a.com", summary="Résumé A", source_name="HN")]
    mock_selection = SelectionResult(
        articles=[SelectedArticle(title="A1", url="https://a.com", category="Tech & IA")]
    )
    markdown_output = "### [Tech & IA] A1\n- **C'est quoi :** Découverte\n- **Pourquoi on en parle :** Impact\n- [Lien](https://a.com)"

    mock_provider = MockLLMProvider(structured_return=mock_selection, text_return=markdown_output)

    classified = await classify_articles(sources, mock_provider)
    assert len(classified.articles) == 1

    briefing = await generate_briefing(classified, sources, mock_provider)
    assert "### [Tech & IA] A1" in briefing
    assert "https://a.com" in briefing
