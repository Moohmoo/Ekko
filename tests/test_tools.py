"""Tests unitaires pour le registre d'outils et les adaptateurs (Brique 3)."""

from datetime import date
from pathlib import Path
from typing import Type
import pytest
from pydantic import BaseModel, Field
from config import Settings
from tools.base import BaseTool
from tools.registry import ToolRegistry
from tools.system import SystemInfoTool
from tools.watch import WatchTool


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
async def test_watch_tool_existing_briefing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie que WatchTool retourne le texte du briefing si déjà existant."""
    today_file = tmp_path / f"{date.today().isoformat()}.md"
    today_file.write_text("# Briefing SOTA\n- Sujet 1", encoding="utf-8")

    dummy_settings = Settings(watch_dir_path=tmp_path)
    monkeypatch.setattr("tools.watch.tool.get_settings", lambda: dummy_settings)

    tool = WatchTool()
    res = await tool.execute(force=False)
    assert "Briefing du jour disponible" in res
    assert "Briefing SOTA" in res
    assert "Sujet 1" in res


@pytest.mark.asyncio
async def test_watch_tool_error_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le message d'erreur lorsque execute_daily_watch échoue."""
    dummy_settings = Settings(watch_dir_path=tmp_path)
    monkeypatch.setattr("tools.watch.tool.get_settings", lambda: dummy_settings)

    async def mock_fail(*args: object, **kwargs: object) -> int:
        return 1

    monkeypatch.setattr("tools.watch.tool.execute_daily_watch", mock_fail)
    tool = WatchTool()
    res = await tool.execute(force=True)
    assert "Une erreur est survenue" in res


@pytest.mark.asyncio
async def test_watch_tool_filter_matching_query(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le filtrage d'articles correspondant à un mot-clé précis."""
    today_file = tmp_path / f"{date.today().isoformat()}.md"
    today_file.write_text(
        "### Tech & IA Paper A: Vision Transformer\n- Résumé vision\n\n"
        "### Tech & IA Paper B: Audio Synthesis\n- Résumé audio",
        encoding="utf-8",
    )
    dummy_settings = Settings(watch_dir_path=tmp_path)
    monkeypatch.setattr("tools.watch.tool.get_settings", lambda: dummy_settings)

    tool = WatchTool()
    res = await tool.execute(query="vision")
    assert "Articles correspondant à 'vision'" in res
    assert "Paper A" in res
    assert "Paper B" not in res


@pytest.mark.asyncio
async def test_watch_tool_filter_no_match_query(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Vérifie le message d'absence d'articles avec les sujets disponibles listés."""
    today_file = tmp_path / f"{date.today().isoformat()}.md"
    today_file.write_text(
        "### Tech & IA Paper A: Vision Transformer\n- Résumé vision",
        encoding="utf-8",
    )
    dummy_settings = Settings(watch_dir_path=tmp_path)
    monkeypatch.setattr("tools.watch.tool.get_settings", lambda: dummy_settings)

    tool = WatchTool()
    res = await tool.execute(query="bioinfo")
    assert "Aucun article ne correspond à 'bioinfo'" in res
    assert "Paper A: Vision Transformer" in res

