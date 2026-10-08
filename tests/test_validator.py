"""Tests unitaires pour l'Agent Validateur / Critique (Evaluator)."""

from typing import TypeVar
import pytest
from pydantic import BaseModel
from agent.validator import format_validation_prompt, validate_draft
from providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockValidatorProvider(LLMProvider):
    """Fournisseur de test pour observer les appels du validateur."""

    def __init__(self, response_text: str = "Réponse validée et épurée") -> None:
        self.response_text = response_text
        self.call_count = 0

    async def generate_structured(
        self, prompt: str, schema: type[T], system_instruction: str = ""
    ) -> T:
        raise NotImplementedError

    async def generate_text(self, prompt: str, system_instruction: str = "") -> str:
        self.call_count += 1
        return self.response_text


@pytest.mark.asyncio
async def test_validator_skips_short_greeting_without_observations() -> None:
    """Vérifie qu'un échange court et informel sans outil court-circuite la validation."""
    provider = MockValidatorProvider()
    res = await validate_draft(
        provider=provider,
        user_query="Salut !",
        draft_answer="Salut Mohamed ! En quoi puis-je t'aider ?",
        observations=[],
        user_profile="Profil ingénieur",
    )
    assert res == "Salut Mohamed ! En quoi puis-je t'aider ?"
    assert provider.call_count == 0


@pytest.mark.asyncio
async def test_validator_purifies_draft_with_observations() -> None:
    """Vérifie que la présence d'observations déclenche la critique du validateur."""
    provider = MockValidatorProvider(response_text="Synthèse épurée des faits.")
    draft = "Voici des tonnes d'infos marketing inutiles."
    observations = ["- Résultat search : [Paper](https://arxiv.org/abs/...)"]

    res = await validate_draft(
        provider=provider,
        user_query="Quelles sont les news ?",
        draft_answer=draft,
        observations=observations,
        user_profile="Profil ingénieur",
    )
    assert res == "Synthèse épurée des faits."
    assert provider.call_count == 1


def test_format_validation_prompt() -> None:
    """Vérifie le formatage structuré du prompt de validation."""
    prompt = format_validation_prompt(
        user_query="AlphaFold 3 ?",
        draft_answer="Projet de réponse",
        observations=["Observation 1", "Observation 2"],
    )
    assert "Demande initiale de l'utilisateur : AlphaFold 3 ?" in prompt
    assert "Observation 1" in prompt
    assert "Observation 2" in prompt
    assert "Projet de réponse à critiquer et valider :\nProjet de réponse" in prompt
