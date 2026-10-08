"""Routeur d'intentions utilisateur (Pattern Dispatcher).

Détermine en amont si une requête relève de la conversation directe,
d'une recherche documentaire approfondie, ou d'une action outillée.
"""

import re
from providers.base import LLMProvider
from .context import ExecutionContext
from .schemas import UserIntent

FAST_GREETINGS = {
    "salut", "bonjour", "bonsoir", "coucou", "yoh", "yo", "hello",
    "hi", "hey", "merci", "merci beaucoup", "thanks", "thx", "ça va",
    "ca va", "comment vas-tu", "comment vas tu", "comment ca va",
    "comment ça va", "qui es-tu", "qui es tu",
}


from .prompts import build_intent_prompt, build_intent_user_prompt


def is_fast_greeting(query: str) -> bool:
    """Détecte instantanément les salutations et politesses courtes sans appel LLM."""
    cleaned = re.sub(r"[^\w\s]", " ", query.lower())
    normalized = " ".join(cleaned.split())
    return normalized in FAST_GREETINGS or query.lower().strip() in FAST_GREETINGS


def is_contextual_recall(query: str, ctx: ExecutionContext | None = None) -> bool:
    """Détecte les demandes explicites de rappel conversationnel quand un historique existe."""
    if not ctx or not ctx.history_block:
        return False
    q = query.lower().strip()
    recall_prefixes = (
        "rappelle", "rappelles", "résume-moi", "resume-moi",
        "tu te souviens", "de quoi on parlait", "peux-tu me rappeler",
        "redonne-moi", "redonnes-moi", "qu'est-ce qu'on disait",
    )
    return any(q.startswith(p) or f" {p}" in q for p in recall_prefixes)


async def classify_intent(
    provider: LLMProvider,
    query: str,
    ctx: ExecutionContext | None = None,
) -> str:
    """Classifie l'intention utilisateur via détection rapide ou appel structuré conscient du contexte."""
    if is_fast_greeting(query) or is_contextual_recall(query, ctx):
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
