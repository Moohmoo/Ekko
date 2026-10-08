"""Tests unitaires pour le routeur d'intentions (Pattern Dispatcher)."""

from collections.abc import AsyncIterator
from typing import TypeVar
import pytest
from pydantic import BaseModel
from agent.context import EnvironmentContext, ExecutionContext
from agent.router import build_intent_user_prompt, classify_intent
from agent.schemas import UserIntent
from providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockRouterLLM(LLMProvider):
    """Fournisseur LLM simulé pour tester la classification d'intention."""

    def __init__(self, intent: str = "research", should_fail: bool = False) -> None:
        self.intent = intent
        self.should_fail = should_fail
        self.call_count = 0
        self.captured_prompt = ""

    async def generate_structured(
        self, prompt: str, schema: type[T], system_instruction: str = ""
    ) -> T:
        self.call_count += 1
        self.captured_prompt = prompt
        if self.should_fail:
            raise RuntimeError("Erreur API simulée")
        return UserIntent(intent=self.intent)  # type: ignore[return-value]

    async def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        return ""

    async def stream_text(
        self, prompt: str, system_instruction: str = ""
    ) -> AsyncIterator[str]:
        yield ""


@pytest.mark.asyncio
async def test_classify_intent_delegates_to_llm() -> None:
    """Vérifie la classification sémantique via LLM pour les requêtes complexes."""
    provider = MockRouterLLM(intent="research")
    intent = await classify_intent(provider, "Avancées sur le repliement d'ARN")

    assert intent == "research"
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_classify_intent_chat_intent() -> None:
    """Vérifie le routage correct vers chat lorsque le modèle classe en chat."""
    provider = MockRouterLLM(intent="chat")
    intent = await classify_intent(provider, "Salut Mohamed !")

    assert intent == "chat"
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_classify_intent_fallback_on_error() -> None:
    """Vérifie le repli sécurisé vers 'chat' en cas d'incident du fournisseur."""
    provider = MockRouterLLM(should_fail=True)
    intent = await classify_intent(provider, "Requête causant une erreur")

    assert intent == "chat"
    assert provider.call_count == 1


def test_build_intent_user_prompt_with_history() -> None:
    """Vérifie l'inclusion de l'historique conversationnel dans le prompt de routage."""
    ctx = ExecutionContext(
        env=EnvironmentContext(
            current_date="8 octobre 2026",
            current_year=2026,
            current_time="16:00",
            os_name="linux",
            cwd="",
        ),
        history_block="[user]: news IA\n[assistant]: résumé des news",
    )
    prompt = build_intent_user_prompt("Et pour le modèle cité plus haut ?", ctx)
    assert "Historique de la conversation :" in prompt
    assert "[user]: news IA" in prompt
    assert "Demande utilisateur :\n\"Et pour le modèle cité plus haut ?\"" in prompt


@pytest.mark.asyncio
async def test_classify_intent_passes_history_context() -> None:
    """Vérifie que classify_intent transmet l'historique de contexte au fournisseur."""
    ctx = ExecutionContext(
        env=EnvironmentContext(
            current_date="8 octobre 2026",
            current_year=2026,
            current_time="16:00",
            os_name="linux",
            cwd="",
        ),
        history_block="[user]: news IA\n[assistant]: résumé des news",
    )
    provider = MockRouterLLM(intent="chat")
    intent = await classify_intent(provider, "Et pour le modèle cité plus haut ?", ctx=ctx)

    assert intent == "chat"
    assert provider.call_count == 1
    assert "Historique de la conversation :" in provider.captured_prompt

