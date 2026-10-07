"""Tests unitaires pour la validation des modèles Pydantic."""

import pytest
from pydantic import ValidationError
from watch.models import Article, SelectedArticle, SelectionResult


def test_article_instantiation() -> None:
    """Vérifie l'instanciation correcte du modèle Article."""
    art = Article(
        title="Nouveau LLM Open Source",
        url="https://example.com/llm",
        summary="Description courte",
        source_name="Hacker News",
    )
    assert art.title == "Nouveau LLM Open Source"
    assert art.source_name == "Hacker News"


def test_selected_article_and_result() -> None:
    """Vérifie le modèle SelectedArticle et la liste SelectionResult."""
    selected = SelectedArticle(
        title="Breakthrough Bio",
        url="https://example.com/bio",
        category="Sciences & Bio",
    )
    result = SelectionResult(articles=[selected])
    assert len(result.articles) == 1
    assert result.articles[0].category == "Sciences & Bio"


def test_invalid_article_raises() -> None:
    """Vérifie qu'un article sans URL ou sans titre lève une ValidationError."""
    with pytest.raises(ValidationError):
        Article.model_validate({"title": "Sans URL"})
