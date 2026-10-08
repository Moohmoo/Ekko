"""Tests unitaires et d'intégration pour le pipeline de recherche déterministe."""

from pathlib import Path
from typing import TypeVar
import pytest
from pydantic import BaseModel
from agent.engine import EkkoEngine
from agent.memory import SQLiteMemory
from agent.pipeline import collect_sources, plan_research, synthesize_findings
from agent.schemas import DoneEvent, PlanEvent, RetrievalEvent, SearchPlan, ValidationEvent
from config import Settings
from providers.base import LLMProvider
from tools.base import BaseTool, EmptyParams
from tools.registry import ToolRegistry

T = TypeVar("T", bound=BaseModel)


class MockPipelineProvider(LLMProvider):
    """Fournisseur LLM simulé pour le pipeline de recherche."""

    def __init__(self, plan: SearchPlan, synthesis_text: str = "Synthèse validée") -> None:
        self.plan = plan
        self.synthesis_text = synthesis_text

    async def generate_structured(
        self, prompt: str, schema: type[T], system_instruction: str = ""
    ) -> T:
        return self.plan  # type: ignore[return-value]

    async def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        return self.synthesis_text


class MockSearchTool(BaseTool):
    """Outil de recherche simulé pour tester la collecte et dédoublonnage."""

    name = "search"
    description = "Mock search"
    parameters_schema = EmptyParams

    async def execute(self, **kwargs: object) -> str:
        q = kwargs.get("query", "")
        return f"1. **[Paper {q}](http://arxiv.org/{q})** - Authors (2026)\n   Abstract content."


@pytest.mark.asyncio
async def test_plan_research() -> None:
    """Vérifie la formulation du plan de recherche via le provider."""
    expected_plan = SearchPlan(
        is_search_needed=True,
        focus="academic",
        queries=["RNA structure folding", "RNA inverse design"],
    )
    provider = MockPipelineProvider(expected_plan)
    plan = await plan_research(provider, "Repliement d'ARN")

    assert plan.is_search_needed is True
    assert plan.focus == "academic"
    assert len(plan.queries) == 2


@pytest.mark.asyncio
async def test_collect_sources_deduplication() -> None:
    """Vérifie que collect_sources fusionne et dédoublonne les blocs identiques."""
    plan = SearchPlan(is_search_needed=True, focus="academic", queries=["q1", "q1"])
    tool = MockSearchTool()
    sources, count, elapsed = await collect_sources(tool, plan)

    assert count == 1  # La deuxième requête identique a été dédoublonnée
    assert "Paper q1" in sources
    assert elapsed >= 0.0


@pytest.mark.asyncio
async def test_synthesize_findings() -> None:
    """Vérifie la synthèse technique formatée."""
    plan = SearchPlan(is_search_needed=True)
    provider = MockPipelineProvider(plan, synthesis_text="- **[Paper](URL)** : résultat")
    res = await synthesize_findings(provider, "Question", "Sources", "Profil")

    assert "- **[Paper](URL)** : résultat" in res


@pytest.mark.asyncio
async def test_engine_pipeline_stream(tmp_path: Path) -> None:
    """Vérifie le flux complet d'événements du pipeline dans EkkoEngine."""
    plan = SearchPlan(
        is_search_needed=True,
        focus="academic",
        queries=["RNA folding"],
    )
    provider = MockPipelineProvider(plan, synthesis_text="Synthèse certifiée avec lien.")
    registry = ToolRegistry()
    registry.register(MockSearchTool())
    memory = SQLiteMemory(tmp_path / "test_pipe.db")
    engine = EkkoEngine(
        settings=Settings(),
        provider=provider,
        registry=registry,
        memory=memory,
        user_profile="Profil",
        use_pipeline=True,
    )

    events = [ev async for ev in engine.run_stream("Repliement ARN")]

    assert len(events) == 4
    assert isinstance(events[0], PlanEvent)
    assert events[0].focus == "academic"
    assert isinstance(events[1], RetrievalEvent)
    assert events[1].count == 1
    assert isinstance(events[2], ValidationEvent)
    assert isinstance(events[3], DoneEvent)
    assert "Synthèse certifiée avec lien." in events[3].response.content
