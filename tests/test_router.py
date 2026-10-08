"""Tests unitaires pour le routeur d'intentions (Pattern Dispatcher)."""

from collections.abc import AsyncIterator
from typing import TypeVar
import pytest
from pydantic import BaseModel
from agent.router import classify_intent, is_fast_greeting
from agent.schemas import UserIntent
from providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockRouterLLM(LLMProvider):
    """Fournisseur LLM simulé pour tester la classification d'intention."""

    def __init__(self, intent: str = "research", should_fail: bool = False) -> None:
        self.intent = intent
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_structured(
        self, prompt: str, schema: type[T], system_instruction: str = ""
    ) -> T:
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Erreur API simulée")
        return UserIntent(intent=self.intent)  # type: ignore[return-value]

    async def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        return ""

    async def stream_text(
        self, prompt: str, system_instruction: str = ""
    ) -> AsyncIterator[str]:
        yield ""


def test_is_fast_greeting_detection() -> None:
    """Vérifie la détection instantanée des salutations courtes et courantes."""
    assert is_fast_greeting("yoh") is True
    assert is_fast_greeting("Yoh !") is True
    assert is_fast_greeting("salut") is True
    assert is_fast_greeting("Bonjour") is True
    assert is_fast_greeting("merci") is True
    assert is_fast_greeting("comment vas-tu ?") is True
    assert is_fast_greeting("Quelles sont les avancées sur l'ARN ?") is False
    assert is_fast_greeting("ajoute un item dans la todo list") is False


@pytest.mark.asyncio
async def test_classify_intent_skips_llm_on_fast_greeting() -> None:
    """Vérifie que les salutations directes ne consomment aucun appel LLM."""
    provider = MockRouterLLM(intent="research")
    intent = await classify_intent(provider, "yoh")

    assert intent == "chat"
    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_classify_intent_delegates_to_llm() -> None:
    """Vérifie la classification via LLM pour les requêtes complexes."""
    provider = MockRouterLLM(intent="research")
    intent = await classify_intent(provider, "Avancées sur le repliement d'ARN")

    assert intent == "research"
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_classify_intent_fallback_on_error() -> None:
    """Vérifie le repli sécurisé vers 'chat' en cas d'incident du fournisseur."""
    provider = MockRouterLLM(should_fail=True)
    intent = await classify_intent(provider, "Requête causant une erreur")

    assert intent == "chat"
    assert provider.call_count == 1
