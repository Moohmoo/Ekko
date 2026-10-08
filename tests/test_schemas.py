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
from tools.reader.tool import ReaderParams
from tools.search.tool import SearchItem, SearchParams


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


def test_search_item() -> None:
    """Vérifie la création et validation du modèle typé SearchItem."""
    item = SearchItem(title="Test Paper", url="https://arxiv.org/abs/1234.5678", snippet="Test abstract")
    assert item.title == "Test Paper"
    assert item.url == "https://arxiv.org/abs/1234.5678"
    assert item.snippet == "Test abstract"
    assert item.source == ""
    assert item.date == ""
    assert item.authors == []


def test_reader_params() -> None:
    """Vérifie la validation des paramètres d'extraction de page (Reader)."""
    params = ReaderParams(url="https://example.com")
    assert params.url == "https://example.com"
    assert params.max_chars == 4000


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
        "focus": {"default": "academic", "type": "string"},
        "queries": {"default": ["RNA folding"], "type": "array"},
    }
    plan = SearchPlan.model_validate(raw_payload)
    assert plan.focus == "academic"
    assert plan.queries == ["RNA folding"]

    # Vérifie que tout champ direct_answer ou parasite est ignoré sans erreur
    extra_payload = {
        "focus": "news",
        "queries": ["models"],
        "direct_answer": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
    }
    plan2 = SearchPlan.model_validate(extra_payload)
    assert plan2.focus == "news"
    assert plan2.queries == ["models"]


def test_schemas_null_thought_and_sentinel_final_answer() -> None:
    """Vérifie la robustesse face aux valeurs nulles et sentinelles retournées par les SLMs."""
    ui = UserIntent.model_validate({"thought": None, "intent": "chat"})
    assert ui.thought == ""

    sp = SearchPlan.model_validate({"thought": None, "queries": []})
    assert sp.thought == ""

    action = AgentAction.model_validate({
        "thought": None,
        "tool_name": "null",
        "final_answer": "null",
    })
    assert action.thought == ""
    assert action.tool_name is None
    assert action.final_answer is None


