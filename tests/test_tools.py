"""Tests unitaires pour le registre d'outils et les adaptateurs natifs."""

from typing import Type
import pytest
from pydantic import BaseModel, Field
from tools.base import BaseTool
from tools.news import NewsSearchTool
from tools.registry import ToolRegistry
from tools.search import WebSearchTool
from tools.system import SystemInfoTool
from tools.web import FetchPageTool


class DummyParams(BaseModel):
    """Paramètres pour outil de test."""

    message: str = Field(description="Message à répéter")


class DummyEchoTool(BaseTool):
    """Outil factice pour tester le cycle du registre."""

    name: str = "dummy_echo"
    description: str = "Répète un message passé en argument."
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
async def test_web_search_tool_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie l'exécution et le formatage des résultats par WebSearchTool."""
    fake_results = [
        {"title": "SFBI Bioinfo", "href": "https://example.com/bioinfo", "body": "Actualités bioinformatique"},
    ]

    def mock_ddgs(query: str, max_results: int) -> list[dict[str, str]]:
        return fake_results

    monkeypatch.setattr("tools.search.tool._perform_ddgs_search", mock_ddgs)
    tool = WebSearchTool()
    res = await tool.execute(query="bioinfo", max_results=3)

    assert "SFBI Bioinfo" in res
    assert "https://example.com/bioinfo" in res
    assert "Actualités bioinformatique" in res


@pytest.mark.asyncio
async def test_web_search_tool_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie la capture d'erreur lors d'une défaillance réseau dans WebSearchTool."""
    def mock_fail(query: str, max_results: int) -> list[dict[str, str]]:
        raise RuntimeError("Réseau indisponible")

    monkeypatch.setattr("tools.search.tool._perform_ddgs_search", mock_fail)
    tool = WebSearchTool()
    res = await tool.execute(query="fail")
    assert "Erreur lors de la recherche" in res


@pytest.mark.asyncio
async def test_fetch_page_tool_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le téléchargement et le nettoyage HTML par FetchPageTool."""
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
    tool = FetchPageTool()
    res = await tool.execute(url="https://example.com/page")

    assert "Titre Paragraphe intéressant" in res
    assert "Contenu extrait" in res


@pytest.mark.asyncio
async def test_news_search_tool_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie l'exécution et le formatage des dépêches par NewsSearchTool."""
    fake_news = [
        {
            "title": "Avancée en bioinformatique",
            "url": "https://example.com/bio-news",
            "source": "Le Monde Informatique",
            "date": "2026-10-06T12:00:00+00:00",
            "body": "Une nouvelle découverte majeure utilisant l'IA.",
        }
    ]

    def mock_ddgs_news(query: str, max_results: int) -> list[dict[str, str]]:
        return fake_news

    monkeypatch.setattr("tools.news.tool._perform_ddgs_news", mock_ddgs_news)
    tool = NewsSearchTool()
    res = await tool.execute(query="bioinformatique", max_results=3)

    assert "Avancée en bioinformatique" in res
    assert "https://example.com/bio-news" in res
    assert "Le Monde Informatique" in res
    assert "2026-10-06" in res
    assert "Une nouvelle découverte majeure" in res


@pytest.mark.asyncio
async def test_news_search_tool_empty_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le message quand aucune actualité n'est trouvée."""
    monkeypatch.setattr("tools.news.tool._perform_ddgs_news", lambda q, m: [])
    tool = NewsSearchTool()
    res = await tool.execute(query="sujet_inconnu")
    assert "Aucune actualité récente trouvée" in res


@pytest.mark.asyncio
async def test_news_search_tool_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie la gestion d'erreur réseau pour NewsSearchTool."""
    def mock_fail(query: str, max_results: int) -> list[dict[str, str]]:
        raise ConnectionError("Service injoignable")

    monkeypatch.setattr("tools.news.tool._perform_ddgs_news", mock_fail)
    tool = NewsSearchTool()
    res = await tool.execute(query="fail")
    assert "Erreur lors de la recherche d'actualités" in res
