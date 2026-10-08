"""Tests unitaires et d'intégration pour le pipeline de recherche déterministe."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import TypeVar
import pytest
from pydantic import BaseModel
from agent.engine import EkkoEngine
from agent.storage import SessionStorage
from agent.pipeline import collect_sources, plan_research, synthesize_findings
from agent.schemas import (
    DoneEvent,
    PlanEvent,
    RetrievalEvent,
    SearchPlan,
    StreamChunkEvent,
    UserIntent,
    ValidationEvent,
)
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
        if schema == UserIntent:
            return UserIntent(intent="research")  # type: ignore[return-value]
        return self.plan  # type: ignore[return-value]

    async def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        return self.synthesis_text

    async def stream_text(
        self, prompt: str, system_instruction: str = ""
    ) -> AsyncIterator[str]:
        yield self.synthesis_text


from typing import Literal
from tools.search import SearchItem, SearchTool


class MockSearchTool(SearchTool):
    """Outil de recherche simulé pour tester la collecte et dédoublonnage."""

    async def search(
        self,
        query: str = "",
        focus: Literal["academic", "code", "news", "web"] = "news",
        max_results: int = 5,
        region: str | None = None,
    ) -> list[SearchItem]:
        return [
            SearchItem(
                title=f"Paper {query}",
                url=f"http://arxiv.org/{query}",
                snippet="Abstract content.",
                source="arXiv",
                date="2026",
            )
        ]


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
    storage = SessionStorage(tmp_path / "test_pipe.db")
    engine = EkkoEngine(
        settings=Settings(),
        provider=provider,
        registry=registry,
        storage=storage,
        user_profile="Profil",
        use_pipeline=True,
    )

    events = [ev async for ev in engine.run_stream("Repliement ARN")]

    assert len(events) == 5
    assert isinstance(events[0], PlanEvent)
    assert events[0].focus == "academic"
    assert isinstance(events[1], RetrievalEvent)
    assert events[1].count == 1
    assert isinstance(events[2], StreamChunkEvent)
    assert events[2].delta == "Synthèse certifiée avec lien."
    assert isinstance(events[3], ValidationEvent)
    assert isinstance(events[4], DoneEvent)
    assert "Synthèse certifiée avec lien." in events[4].response.content
