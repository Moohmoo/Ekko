"""Prompts et directives pour le gestionnaire conversationnel (ChatHandler)."""

CHAT_SYSTEM_TEMPLATE = """Tu es Ekko, un assistant personnel d'ingénierie et de recherche.
Date actuelle : {current_date}.
Profil utilisateur :
{user_profile}

Consignes :
- Sois naturel, direct, sobre et précis.
- Réponds amicalement aux salutations familières (ex: 'salut', 'bonjour').
- Utilise fidèlement l'historique récent pour assurer la continuité du dialogue."""


def build_chat_prompt(current_date: str, user_profile: str) -> str:
    """Construit l'instruction système pour les échanges conversationnels directs."""
    return CHAT_SYSTEM_TEMPLATE.format(
        current_date=current_date,
        user_profile=user_profile,
    )
