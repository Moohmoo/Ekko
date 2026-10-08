"""Tests unitaires pour le registre d'outils et les adaptateurs universels."""

from typing import Type
import pytest
from pydantic import BaseModel, Field
from tools.base import BaseTool
from tools.reader import ReaderTool
from tools.registry import ToolRegistry
from tools.search import SearchItem, SearchTool
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
async def test_registry_case_insensitive_lookup() -> None:
    """Vérifie la résolution insensible à la casse des outils et alias."""
    registry = ToolRegistry()
    registry.register(SearchTool())
    registry.register(ReaderTool())

    assert registry.get_tool("SEARCH") is not None
    assert registry.get_tool("Search") is not None
    assert registry.get_tool("WEB_SEARCH") is not None
    assert registry.get_tool("Reader") is not None


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


def test_get_gpu_brief_multigpu(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le parsing résilient sur les configurations multi-GPU."""
    import subprocess
    from tools.system.tool import get_gpu_brief

    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/nvidia-smi")
    fake_output = "NVIDIA RTX 4090, 100, 24576\nNVIDIA RTX 4090, 200, 24576\n"
    fake_res = subprocess.CompletedProcess(args=[], returncode=0, stdout=fake_output)
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: fake_res)

    brief = get_gpu_brief()
    assert "NVIDIA RTX 4090 : 100 Mo / 24576 Mo VRAM" in brief
    assert " | " in brief


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
async def test_search_tool_search_returns_typed_items(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie que search() retourne des instances typées de SearchItem."""
    fake_items = [
        {"title": "Paper 1", "url": "https://example.com/1", "body": "Snippet 1"},
    ]
    monkeypatch.setattr("tools.search.tool._perform_ddgs_web", lambda q, m, r: fake_items)
    tool = SearchTool()
    items = await tool.search(query="test", focus="web")

    assert len(items) == 1
    assert isinstance(items[0], SearchItem)
    assert items[0].title == "Paper 1"
    assert items[0].url == "https://example.com/1"
    assert items[0].snippet == "Snippet 1"


def test_perform_ddgs_web_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le repli gracieux de _perform_ddgs_web en cas d'incident réseau DDGS."""
    from tools.search.tool import _perform_ddgs_web

    class MockFailingDDGS:
        def __enter__(self):
            raise ConnectionError("DNS resolution failed")
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("tools.search.tool.DDGS", MockFailingDDGS)
    res = _perform_ddgs_web("test", 5, "fr-fr")
    assert res == []


def test_build_arxiv_search_query() -> None:
    """Vérifie la construction propre des requêtes booléennes arXiv."""
    from tools.search.tool import _build_arxiv_search_query

    assert _build_arxiv_search_query("machine learning") == "all:machine AND all:learning"
    assert _build_arxiv_search_query("") == ""
    assert _build_arxiv_search_query("   ") == ""


@pytest.mark.asyncio
async def test_reader_tool_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le téléchargement et le nettoyage HTML par ReaderTool."""
    from contextlib import asynccontextmanager
    html_content = "<html><body><h1>Titre</h1><p>Paragraphe intéressant</p></body></html>"

    class MockResponse:
        text = html_content
        headers = {"content-type": "text/html"}
        encoding = "utf-8"

        def raise_for_status(self) -> None:
            pass

        async def aiter_bytes(self):
            yield html_content.encode("utf-8")

    class MockAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object):
            pass

        @asynccontextmanager
        async def stream(self, *args: object, **kwargs: object):
            yield MockResponse()

    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)
    tool = ReaderTool()
    res = await tool.execute(url="https://example.com/page")

    assert "Titre Paragraphe intéressant" in res
    assert "Contenu extrait" in res

    # Vérifie également le cas sans schéma explicite
    res_no_scheme = await tool.execute(url="example.com/page")
    assert "Contenu extrait de `https://example.com/page`" in res_no_scheme


@pytest.mark.asyncio
async def test_reader_tool_binary_and_oversize(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le rejet sécurisé des formats binaires et fichiers trop volumineux."""
    from contextlib import asynccontextmanager

    class MockBinaryResponse:
        headers = {"content-type": "application/octet-stream"}
        encoding = "utf-8"

        def raise_for_status(self) -> None:
            pass

        async def aiter_bytes(self):
            yield b"x" * 100

    class MockAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object):
            pass

        @asynccontextmanager
        async def stream(self, *args: object, **kwargs: object):
            yield MockBinaryResponse()

    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)
    tool = ReaderTool()
    res = await tool.execute(url="https://example.com/archive.bin")
    assert "n'est pas un format textuel lisible" in res


def test_get_region_for_language_mapping() -> None:
    """Vérifie le mappage cohérent des langues système vers les régions de recherche."""
    from config import get_region_for_language

    assert get_region_for_language("fr") == "fr-fr"
    assert get_region_for_language("en") == "en-us"
    assert get_region_for_language("de") == "de-de"
    assert get_region_for_language("unknown") == "wt-wt"


@pytest.mark.asyncio
async def test_fetch_arxiv_entries_handles_malformed_author(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie que les balises author sans balise name ne font pas échouer l'ensemble du flux arXiv."""
    from tools.search.tool import _fetch_arxiv_entries

    xml_data = """<feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Valid Paper</title>
        <id>http://arxiv.org/abs/2601.0001</id>
        <summary>A good abstract.</summary>
        <published>2026-01-01T00:00:00Z</published>
        <author><email>no-name@arxiv.org</email></author>
        <author><name>Alice Smith</name></author>
      </entry>
    </feed>"""

    class MockResp:
        status_code = 200
        text = xml_data

    class MockClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object):
            pass

        async def get(self, *args: object, **kwargs: object):
            return MockResp()

    monkeypatch.setattr("httpx.AsyncClient", MockClient)
    entries = await _fetch_arxiv_entries("quantum", max_results=5)
    assert len(entries) == 1
    assert entries[0].title == "Valid Paper"
    assert entries[0].authors == ["Alice Smith"]


@pytest.mark.asyncio
async def test_reader_tool_oversized_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie que les documents dépassant 2 Mo sont stoppés sans saturer la mémoire."""
    from contextlib import asynccontextmanager

    class MockOversizedResponse:
        headers = {
            "content-type": "text/html",
            "content-length": str(5 * 1024 * 1024),
        }
        encoding = "utf-8"

        def raise_for_status(self) -> None:
            pass

        async def aiter_bytes(self):
            yield b"x" * 100

    class MockClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: object):
            pass

        @asynccontextmanager
        async def stream(self, *args: object, **kwargs: object):
            yield MockOversizedResponse()

    monkeypatch.setattr("httpx.AsyncClient", MockClient)
    tool = ReaderTool()
    res = await tool.execute(url="https://example.com/large.html")
    assert "dépasse la taille maximale autorisée" in res
