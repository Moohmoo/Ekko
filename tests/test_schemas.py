"""Tests unitaires pour la validation des modèles et contrats Pydantic."""

import pytest
from pydantic import ValidationError
from agent.schemas import AgentAction, AgentRequest, AgentResponse
from tools.search.tool import WebSearchParams
from tools.web.tool import FetchPageParams


def test_agent_request_and_response() -> None:
    """Vérifie les contrats AgentRequest et AgentResponse."""
    req = AgentRequest(query="Yoh !", session_id="test_sess")
    assert req.query == "Yoh !"
    assert req.session_id == "test_sess"

    resp = AgentResponse(content="Salut !", tools_used=["web_search"], thought="Penser")
    assert resp.content == "Salut !"
    assert resp.tools_used == ["web_search"]
    assert resp.thought == "Penser"


def test_agent_action_defaults() -> None:
    """Vérifie les valeurs par défaut du schéma AgentAction."""
    action = AgentAction(thought="Reflexion")
    assert action.thought == "Reflexion"
    assert action.tool_name is None
    assert action.tool_arguments == {}
    assert action.final_answer is None


def test_web_search_params() -> None:
    """Vérifie la validation des paramètres de recherche."""
    params = WebSearchParams(query="bioinformatique")
    assert params.query == "bioinformatique"
    assert params.max_results == 5

    with pytest.raises(ValidationError):
        WebSearchParams()  # type: ignore[call-arg]


def test_fetch_page_params() -> None:
    """Vérifie la validation des paramètres d'extraction de page."""
    params = FetchPageParams(url="https://example.com")
    assert params.url == "https://example.com"
    assert params.max_chars == 3000
