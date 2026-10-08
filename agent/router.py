"""Routeur d'intentions utilisateur (Pattern Dispatcher).

Détermine en amont si une requête relève de la conversation directe,
d'une recherche documentaire approfondie, ou d'une action outillée.
"""

from providers.base import LLMProvider
from .context import ExecutionContext
from .prompts import build_intent_prompt, build_intent_user_prompt
from .schemas import UserIntent


async def classify_intent(
    provider: LLMProvider,
    query: str,
    ctx: ExecutionContext | None = None,
) -> str:
    if not query or not query.strip():
        return "chat"
    prompt = build_intent_user_prompt(query, ctx)
    sys_prompt = build_intent_prompt(ctx)
    try:
        decision = await provider.generate_structured(
            prompt=prompt,
            schema=UserIntent,
            system_instruction=sys_prompt,
        )
        return decision.intent
    except Exception:
        return "chat"
