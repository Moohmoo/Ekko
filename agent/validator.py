"""Agent Validateur et Critique de conformité pour Ekko (Evaluator / Checker).

Garantit la rigueur scientifique et technique des réponses en élaguant
le bruit marketing, les spéculations et les hallucinations non sourcées.
"""

from providers.base import LLMProvider

from .prompts import (
    VALIDATOR_SYSTEM_PROMPT,
    build_validator_prompt,
    format_validation_prompt,
)


def _has_primary_sources(observations: list[str]) -> bool:
    """Détecte la présence de sources scientifiques ou techniques fiables dans les observations."""
    obs_text = " ".join(observations).lower()
    return any(marker in obs_text for marker in ("arxiv.org", "github.com", "doi.org"))


async def validate_draft(
    provider: LLMProvider,
    user_query: str,
    draft_answer: str,
    observations: list[str],
    user_profile: str,
) -> str:
    """Critique, épure et certifie le brouillon final produit par l'enquêteur ReAct."""
    if not observations and len(draft_answer.strip().split()) < 25:
        return draft_answer

    system_instruction = build_validator_prompt(user_profile)
    prompt = format_validation_prompt(user_query, draft_answer, observations)
    validated = (await provider.generate_text(
        prompt=prompt,
        system_instruction=system_instruction,
    )).strip()

    if not validated:
        return draft_answer
    if _has_primary_sources(observations) and "aucune source" in validated.lower():
        return draft_answer
    return validated
