"""Routeur d'intentions utilisateur (Pattern Dispatcher).

Détermine en amont si une requête relève de la conversation directe,
d'une recherche documentaire approfondie, ou d'une action outillée.
"""

import re
from providers.base import LLMProvider
from .schemas import UserIntent

FAST_GREETINGS = {
    "salut", "bonjour", "bonsoir", "coucou", "yoh", "yo", "hello",
    "hi", "hey", "merci", "merci beaucoup", "thanks", "thx", "ça va",
    "ca va", "comment vas-tu", "comment vas tu", "comment ca va",
    "comment ça va", "qui es-tu", "qui es tu",
}

INTENT_SYSTEM_PROMPT = """Classifie la demande en une seule catégorie stricte :
- 'chat' : salutation, politesse, bavardage, question théorique ne nécessitant aucune recherche externe.
- 'research' : veille technique, actualités récentes, articles scientifiques, bioinfo, code, SOTA.
- 'action' : commande d'action (tâches todo, manipulation de fichiers, commandes système)."""


def is_fast_greeting(query: str) -> bool:
    """Détecte instantanément les salutations et politesses courtes sans appel LLM."""
    cleaned = re.sub(r"[^\w\s]", " ", query.lower())
    normalized = " ".join(cleaned.split())
    return normalized in FAST_GREETINGS or query.lower().strip() in FAST_GREETINGS


async def classify_intent(provider: LLMProvider, query: str) -> str:
    """Classifie l'intention utilisateur via détection rapide ou appel structuré."""
    if is_fast_greeting(query):
        return "chat"

    prompt = f"Demande utilisateur : {query.strip()}"
    try:
        decision = await provider.generate_structured(
            prompt=prompt,
            schema=UserIntent,
            system_instruction=INTENT_SYSTEM_PROMPT,
        )
        return decision.intent
    except Exception:
        return "chat"
