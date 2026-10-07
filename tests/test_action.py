"""Tests unitaires pour le routeur LLM et le schéma AgentAction (Brique 1)."""

import pytest
from agent.schemas import AgentAction


def test_agent_action_valid_arguments() -> None:
    """Vérifie la désérialisation correcte d'arguments JSON valides."""
    action = AgentAction(
        thought="Analyse du besoin",
        tool_name="web_search",
        tool_arguments_json='{"query": "bioinformatique"}',
    )
    assert action.thought == "Analyse du besoin"
    assert action.tool_name == "web_search"
    assert action.tool_arguments == {"query": "bioinformatique"}


def test_agent_action_fallback_on_invalid_json() -> None:
    """Vérifie le repli sur un dictionnaire vide si le JSON est corrompu."""
    action = AgentAction(
        thought="Réflexion",
        tool_name="test_tool",
        tool_arguments_json="invalid json string",
    )
    assert action.tool_arguments == {}


@pytest.mark.parametrize(
    "raw_name,expected",
    [
        ("null", None),
        ("None", None),
        ("none", None),
        ("false", None),
        ("", None),
        ("  web_search  ", "web_search"),
    ],
)
def test_agent_action_sanitize_tool_name(raw_name: str, expected: str | None) -> None:
    """Vérifie le nettoyage des valeurs sentinelles dans tool_name."""
    action = AgentAction(thought="Test", tool_name=raw_name)
    assert action.tool_name == expected
