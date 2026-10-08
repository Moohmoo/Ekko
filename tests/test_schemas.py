"""Tests unitaires pour la validation des modèles et contrats Pydantic."""

import pytest
from pydantic import ValidationError
from agent.schemas import (
    AgentAction,
    AgentRequest,
    AgentResponse,
    SearchPlan,
    UserIntent,
)
from tools.reader.tool import FetchPageParams, ReaderParams
from tools.search.tool import SearchParams, WebSearchParams


def test_agent_request_and_response() -> None:
    """Vérifie les contrats AgentRequest et AgentResponse."""
    req = AgentRequest(query="Yoh !", session_id="test_sess")
    assert req.query == "Yoh !"
    assert req.session_id == "test_sess"

    resp = AgentResponse(content="Salut !", tools_used=["search"], thought="Penser")
    assert resp.content == "Salut !"
    assert resp.tools_used == ["search"]
    assert resp.thought == "Penser"


def test_agent_action_defaults() -> None:
    """Vérifie les valeurs par défaut du schéma AgentAction."""
    action = AgentAction(thought="Reflexion")
    assert action.thought == "Reflexion"
    assert action.tool_name is None
    assert action.tool_arguments == {}
    assert action.final_answer is None


def test_search_params() -> None:
    """Vérifie la validation des paramètres de recherche universelle."""
    params = SearchParams(query="bioinformatique")
    assert params.query == "bioinformatique"
    assert params.focus == "news"
    assert params.max_results == 5

    academic_params = SearchParams(query="AlphaFold", focus="academic", max_results=3)
    assert academic_params.focus == "academic"
    assert academic_params.max_results == 3

    code_params = SearchParams(query="vLLM", focus="code")
    assert code_params.focus == "code"

    with pytest.raises(ValidationError):
        SearchParams()  # type: ignore[call-arg]


def test_reader_params() -> None:
    """Vérifie la validation des paramètres d'extraction de page (Reader)."""
    params = ReaderParams(url="https://example.com")
    assert params.url == "https://example.com"
    assert params.max_chars == 4000

    legacy_params = FetchPageParams(url="https://example.com", max_chars=1500)
    assert legacy_params.url == "https://example.com"
    assert legacy_params.max_chars == 1500


def test_user_intent_with_thought_and_normalization() -> None:
    """Vérifie la robustesse de désérialisation de UserIntent avec thought et dicts de schéma."""
    ui1 = UserIntent.model_validate({"thought": "Analyse de la demande", "intent": "research"})
    assert ui1.thought == "Analyse de la demande"
    assert ui1.intent == "research"

    ui2 = UserIntent.model_validate({"intent": {"default": "chat"}})
    assert ui2.intent == "chat"


def test_search_plan_schema_mimicry_tolerance() -> None:
    """Vérifie que SearchPlan tolère les fragments de schéma JSON émis par les SLMs."""
    raw_payload = {
        "is_search_needed": {"default": True, "type": "boolean"},
        "focus": {"default": "academic", "type": "string"},
        "queries": {"default": ["RNA folding"], "type": "array"},
    }
    plan = SearchPlan.model_validate(raw_payload)
    assert plan.is_search_needed is True
    assert plan.focus == "academic"
    assert plan.queries == ["RNA folding"]

