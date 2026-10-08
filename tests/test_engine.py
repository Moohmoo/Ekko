"""Tests d'intégration pour le moteur ReAct EkkoEngine (Brique 2)."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Type, TypeVar
import pytest
from pydantic import BaseModel
from config import Settings
from agent.engine import EkkoEngine
from agent.memory import SQLiteMemory
from agent.schemas import (
    AgentAction,
    AgentEvent,
    AgentResponse,
    DoneEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
    ValidationEvent,
)
from providers.base import LLMProvider
from tools.base import BaseTool
from tools.registry import ToolRegistry

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Fournisseur LLM factice rejouant une séquence d'actions."""

    def __init__(self, actions: list[AgentAction]) -> None:
        self.actions = actions
        self.call_count = 0

    async def generate_structured(
        self, prompt: str, schema: type[T], system_instruction: str = ""
    ) -> T:
        action = self.actions[self.call_count]
        self.call_count += 1
        return action  # type: ignore[return-value]

    async def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        if "Projet de réponse à critiquer et valider :" in prompt:
            parts = prompt.split("Projet de réponse à critiquer et valider :\n")
            if len(parts) > 1:
                return parts[1].split("\n\nConsigne")[0].strip()
        return "mock text"

    async def stream_text(
        self, prompt: str, system_instruction: str = ""
    ) -> AsyncIterator[str]:
        text = await self.generate_text(prompt, system_instruction)
        yield text


class MockToolParams(BaseModel):
    query: str = ""


class MockTool(BaseTool):
    name = "mock_search"
    description = "Recherche factice"
    parameters_schema: Type[BaseModel] = MockToolParams

    async def execute(self, **kwargs: object) -> str:
        return f"Trouvé: {kwargs.get('query')}"


def setup_engine(tmp_path: Path, actions: list[AgentAction]) -> tuple[EkkoEngine, SQLiteMemory]:
    """Prépare un moteur et sa mémoire temporaire pour les tests."""
    settings = Settings()
    memory = SQLiteMemory(tmp_path / "test_engine.db")
    registry = ToolRegistry()
    registry.register(MockTool())
    provider = MockLLMProvider(actions)
    engine = EkkoEngine(
        settings=settings,
        provider=provider,
        registry=registry,
        memory=memory,
        user_profile="Profil de test",
        max_steps=3,
    )
    return engine, memory


async def consume_engine(
    engine: EkkoEngine, req: str, session_id: str = "default"
) -> tuple[list[AgentEvent], AgentResponse]:
    """Consomme le flux run_stream et retourne les événements et la réponse finale."""
    events: list[AgentEvent] = []
    async for ev in engine.run_stream(req, session_id=session_id):
        events.append(ev)
        if isinstance(ev, DoneEvent):
            return events, ev.response
    raise RuntimeError("Aucun DoneEvent émis par le flux")


@pytest.mark.asyncio
async def test_engine_direct_answer(tmp_path: Path) -> None:
    """Vérifie la résolution immédiate sans appel d'outil."""
    actions = [AgentAction(thought="Réponse directe", final_answer="Voici l'information")]
    engine, memory = setup_engine(tmp_path, actions)

    events, res = await consume_engine(engine, "Question simple", session_id="test_sess")

    assert res.content == "Voici l'information"
    assert res.tools_used == []
    assert any(isinstance(ev, ThoughtEvent) and ev.thought == "Réponse directe" for ev in events)
    history = memory.get_recent_messages("test_sess")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_engine_tool_call_flow(tmp_path: Path) -> None:
    """Vérifie le cycle complet Thought -> Tool Call -> Observation -> Final Answer."""
    actions = [
        AgentAction(
            thought="Besoin de chercher",
            tool_name="mock_search",
            tool_arguments_json='{"query": "antigravity"}',
        ),
        AgentAction(
            thought="Résultat trouvé, conclusion",
            final_answer="La recherche a trouvé antigravity.",
        ),
    ]
    engine, memory = setup_engine(tmp_path, actions)

    events, res = await consume_engine(engine, "Trouve antigravity")

    assert "antigravity" in res.content
    assert res.tools_used == ["mock_search"]
    assert any(isinstance(ev, ToolCallEvent) and ev.tool_name == "mock_search" for ev in events)
    assert any(isinstance(ev, ToolResultEvent) and "antigravity" in ev.result for ev in events)
    tasks = memory.get_recent_tasks()
    assert len(tasks) == 1
    assert tasks[0]["tool_name"] == "mock_search"


@pytest.mark.asyncio
async def test_engine_max_steps_safeguard(tmp_path: Path) -> None:
    """Vérifie le déclenchement du garde-fou si la boucle ne converge pas."""
    loop_action = AgentAction(
        thought="En boucle...",
        tool_name="mock_search",
        tool_arguments_json='{"query": "loop"}',
    )
    actions = [loop_action, loop_action, loop_action]
    engine, _ = setup_engine(tmp_path, actions)

    _, res = await consume_engine(engine, "Boucle sans fin")
    assert "Limite maximale d'étapes" in res.content


@pytest.mark.asyncio
async def test_engine_conversation_history_passed(tmp_path: Path) -> None:
    """Vérifie que l'historique conversationnel est bien conservé et chaîné."""
    actions = [
        AgentAction(thought="Tour 1", final_answer="Réponse 1"),
        AgentAction(thought="Tour 2", final_answer="Réponse 2"),
    ]
    engine, memory = setup_engine(tmp_path, actions)

    await consume_engine(engine, "Première question", session_id="multi_turn")
    await consume_engine(engine, "Seconde question", session_id="multi_turn")

    history = memory.get_recent_messages("multi_turn")
    assert len(history) == 4
    assert history[0]["content"] == "Première question"
    assert history[1]["content"] == "Réponse 1"
    assert history[2]["content"] == "Seconde question"
    assert history[3]["content"] == "Réponse 2"


@pytest.mark.asyncio
async def test_engine_run_stream_events(tmp_path: Path) -> None:
    """Vérifie l'émission séquentielle des événements typés via run_stream incluant la validation."""
    actions = [
        AgentAction(
            thought="Recherche requise",
            tool_name="mock_search",
            tool_arguments_json='{"query": "ekko"}',
        ),
        AgentAction(
            thought="Synthèse",
            final_answer="Voici ekko.",
        ),
    ]
    engine, _ = setup_engine(tmp_path, actions)
    events = [ev async for ev in engine.run_stream("Cherche ekko")]

    assert len(events) == 6
    assert isinstance(events[0], ThoughtEvent)
    assert events[0].thought == "Recherche requise"
    assert isinstance(events[1], ToolCallEvent)
    assert events[1].tool_name == "mock_search"
    assert isinstance(events[2], ToolResultEvent)
    assert "ekko" in events[2].result
    assert isinstance(events[3], ThoughtEvent)
    assert events[3].thought == "Synthèse"
    assert isinstance(events[4], ValidationEvent)
    assert events[4].content == "Voici ekko."
    assert isinstance(events[5], DoneEvent)
    assert events[5].response.content == "Voici ekko."


@pytest.mark.asyncio
async def test_engine_redundant_action_intercepted(tmp_path: Path) -> None:
    """Vérifie que la répétition d'un même outil est interceptée par le moteur."""
    repeated_action = AgentAction(
        thought="Même recherche",
        tool_name="mock_search",
        tool_arguments_json='{"query": "antigravity"}',
    )
    final_action = AgentAction(
        thought="Conclusion forcée",
        final_answer="Réponse finale après avertissement.",
    )
    engine, _ = setup_engine(tmp_path, [repeated_action, repeated_action, final_action])
    events = [ev async for ev in engine.run_stream("Recherche en double")]

    tool_results = [ev for ev in events if isinstance(ev, ToolResultEvent)]
    assert len(tool_results) == 2
    assert "antigravity" in tool_results[0].result
    assert "Action redondante" in tool_results[1].result
