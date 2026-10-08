"""Tests unitaires pour le registre d'outils et les adaptateurs universels."""

from typing import Type
import pytest
from pydantic import BaseModel, Field
from tools.base import BaseTool
from tools.reader import FetchPageTool, ReaderTool
from tools.registry import ToolRegistry
from tools.search import SearchTool, WebSearchTool
from tools.system import SystemInfoTool


class DummyParams(BaseModel):
    """Paramètres pour outil de test."""

    message: str = Field(description="Message à répéter")


class DummyEchoTool(BaseTool):
    """Outil factice pour tester le cycle du registre."""

    name = "dummy_echo"
    description = "Répète un message passé en argument."
    parameters_schema: Type[BaseModel] = DummyParams

    async def execute(self, **kwargs: object) -> str:
        return f"Echo: {kwargs.get('message')}"


@pytest.mark.asyncio
async def test_registry_registration_and_execution() -> None:
    """Vérifie l'enregistrement et l'exécution conforme d'un outil."""
    registry = ToolRegistry()
    registry.register(DummyEchoTool())

    assert registry.get_tool("dummy_echo") is not None
    assert len(registry.list_tools()) == 1

    result = await registry.execute_tool("dummy_echo", {"message": "hello"})
    assert result == "Echo: hello"


@pytest.mark.asyncio
async def test_registry_tool_aliases() -> None:
    """Vérifie la résolution automatique des alias canoniques (web_search -> search, fetch_page -> reader)."""
    registry = ToolRegistry()
    registry.register(SearchTool())
    registry.register(ReaderTool())

    assert registry.get_tool("search") is not None
    assert registry.get_tool("web_search") is not None
    assert registry.get_tool("reader") is not None
    assert registry.get_tool("fetch_page") is not None


@pytest.mark.asyncio
async def test_registry_unknown_tool_handling() -> None:
    """Vérifie le message d'erreur explicite pour un outil inconnu."""
    registry = ToolRegistry()
    result = await registry.execute_tool("unknown_tool", {})
    assert "Erreur" in result
    assert "unknown_tool" in result


@pytest.mark.asyncio
async def test_registry_invalid_arguments_handling() -> None:
    """Vérifie la capture des erreurs de validation Pydantic."""
    registry = ToolRegistry()
    registry.register(DummyEchoTool())

    result = await registry.execute_tool("dummy_echo", {})
    assert "Erreur durant l'exécution" in result


def test_registry_prompt_catalog_formatting() -> None:
    """Vérifie le formatage du catalogue d'outils destiné au prompt système."""
    registry = ToolRegistry()
    registry.register(DummyEchoTool())

    catalog = registry.get_prompt_catalog()
    assert "- Nom : `dummy_echo`" in catalog
    assert "Répète un message" in catalog


@pytest.mark.asyncio
async def test_system_info_tool_execution() -> None:
    """Vérifie l'exécution réelle de l'outil d'informations système."""
    tool = SystemInfoTool()
    info = await tool.execute()
    assert "OS" in info
    assert "Accélération matérielle" in info


@pytest.mark.asyncio
async def test_search_tool_web_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie l'exécution de la recherche en mode web."""
    fake_results = [
        {"title": "SFBI Bioinfo", "href": "https://example.com/bioinfo", "body": "Actualités bioinformatique"},
    ]

    def mock_ddgs(query: str, max_results: int, region: str = "fr-fr") -> list[dict[str, str]]:
        return fake_results

    monkeypatch.setattr("tools.search.tool._perform_ddgs_web", mock_ddgs)
    tool = SearchTool()
    res = await tool.execute(query="bioinfo", focus="web", max_results=3)

    assert "SFBI Bioinfo" in res
    assert "https://example.com/bioinfo" in res
    assert "Actualités bioinformatique" in res


@pytest.mark.asyncio
async def test_search_tool_academic_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie l'exécution de la recherche scientifique (focus academic / arXiv)."""
    fake_papers = [
        {
            "title": "AlphaFold 3 in Action",
            "abstract": "We present diffusion-based biomolecular modeling.",
            "url": "https://arxiv.org/abs/2405.00001",
            "date": "2024-05-08",
            "authors": ["John Jumper", "Demis Hassabis"],
        }
    ]

    async def mock_arxiv(query: str, max_results: int) -> list[dict[str, object]]:
        return fake_papers

    monkeypatch.setattr("tools.search.tool._fetch_arxiv_entries", mock_arxiv)
    tool = SearchTool()
    res = await tool.execute(query="AlphaFold 3", focus="academic", max_results=1)

    assert "Articles scientifiques arXiv" in res
    assert "AlphaFold 3 in Action" in res
    assert "John Jumper" in res
    assert "2024-05-08" in res
    assert "https://arxiv.org/abs/2405.00001" in res


@pytest.mark.asyncio
async def test_search_tool_code_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie l'exécution de la recherche de dépôts GitHub (focus code)."""
    fake_repos = [
        {
            "name": "google-deepmind/alphafold",
            "url": "https://github.com/google-deepmind/alphafold",
            "description": "Open source code for AlphaFold",
            "stars": 15000,
            "language": "Python",
        }
    ]

    async def mock_github(query: str, max_results: int) -> list[dict[str, object]]:
        return fake_repos

    monkeypatch.setattr("tools.search.tool._fetch_github_repos", mock_github)
    tool = SearchTool()
    res = await tool.execute(query="alphafold", focus="code", max_results=1)

    assert "Dépôts de code GitHub" in res
    assert "google-deepmind/alphafold" in res
    assert "15000" in res
    assert "Python" in res


@pytest.mark.asyncio
async def test_search_tool_news_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie l'exécution de la recherche d'actualités récentes (focus news)."""
    fake_news = [
        {
            "title": "Mistral Large 4 Le Chonk Release",
            "url": "https://example.com/mistral-large-4",
            "source": "TechDaily",
            "date": "2026-10-06T12:00:00+00:00",
            "body": "Mistral launches new flagship model with 1T parameters.",
        }
    ]

    def mock_news(query: str, max_results: int, region: str) -> list[dict[str, object]]:
        return fake_news

    monkeypatch.setattr("tools.search.tool._perform_ddgs_news", mock_news)
    tool = SearchTool()
    res = await tool.execute(query="mistral", focus="news", max_results=1)

    assert "Articles et annonces d'actualité récentes" in res
    assert "Mistral Large 4 Le Chonk Release" in res
    assert "https://example.com/mistral-large-4" in res
    assert "TechDaily" in res
    assert "2026-10-06" in res


@pytest.mark.asyncio
async def test_reader_tool_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le téléchargement et le nettoyage HTML par ReaderTool."""
    html_content = "<html><body><h1>Titre</h1><p>Paragraphe intéressant</p></body></html>"

    class MockResponse:
        text = html_content

        def raise_for_status(self) -> None:
            pass

    class MockAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object):
            pass

        async def get(self, *args: object, **kwargs: object):
            return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)
    tool = ReaderTool()
    res = await tool.execute(url="https://example.com/page")

    assert "Titre Paragraphe intéressant" in res
    assert "Contenu extrait" in res


def test_get_region_for_language_mapping() -> None:
    """Vérifie le mappage cohérent des langues système vers les régions de recherche."""
    from config import get_region_for_language

    assert get_region_for_language("fr") == "fr-fr"
    assert get_region_for_language("en") == "en-us"
    assert get_region_for_language("de") == "de-de"
    assert get_region_for_language("unknown") == "wt-wt"
