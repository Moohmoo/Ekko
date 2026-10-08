"""Agent Validateur et Critique de conformité pour Ekko (Evaluator / Checker).

Garantit la rigueur scientifique et technique des réponses en élaguant
le bruit marketing, les spéculations et les hallucinations non sourcées.
"""

from providers.base import LLMProvider
from .prompts import build_validator_prompt, format_validation_prompt


def _contains_url(text: str) -> bool:
    """Détecte la présence d'au moins un lien web (HTTP/HTTPS) dans le texte."""
    return "http://" in text or "https://" in text


async def validate_draft(
    provider: LLMProvider,
    user_query: str,
    draft_answer: str,
    observations: list[str],
    user_profile: str,
) -> str:
    """Critique, épure et certifie le brouillon final produit par l'enquêteur ReAct."""
    if not observations or not draft_answer.strip():
        return draft_answer

    system_instruction = build_validator_prompt(user_profile)
    prompt = format_validation_prompt(user_query, draft_answer, observations)
    validated = (
        await provider.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
        )
    ).strip()

    if not validated:
        return draft_answer

    obs_text = " ".join(observations)
    if _contains_url(obs_text) and _contains_url(draft_answer) and not _contains_url(validated):
        return draft_answer

    return validated
