"""Tests unitaires pour le registre d'outils et les adaptateurs (Brique 3)."""

from typing import Type
import pytest
from pydantic import BaseModel, Field
from tools.base import BaseTool
from tools.registry import ToolRegistry
from tools.system_tool import SystemInfoTool


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
