"""Prompts de classification d'intention pour le routeur."""

from typing import Any

ROUTER_SYSTEM_TEMPLATE = """Tu es le Routeur d'Ekko. Tu classifies la dernière demande de l'utilisateur.{date_info}
RÈGLES STRICTES :
- 'chat' : salutation, discussion, question théorique, ou rappel/question portant sur l'historique récent de la conversation (ne nécessite aucune recherche web externe).
- 'research' : veille technologique, actualités récentes, nouveaux modèles/articles scientifiques, bioinformatique, code nécessitant une recherche web ou académique.
- 'action' : tâches todo, commandes système, manipulation de fichiers ou outils."""


def build_intent_prompt(
    ctx_or_date: Any = "",
    current_year: int = 2026,
) -> str:
    """Construit le prompt de classification enrichi de l'ancrage temporel."""
    if hasattr(ctx_or_date, "current_date"):
        date_str = getattr(ctx_or_date, "current_date", "")
        year_val = getattr(ctx_or_date, "current_year", current_year)
    else:
        date_str = str(ctx_or_date)
        year_val = current_year

    date_info = f"\nDate du jour : {date_str} (Année : {year_val})." if date_str else ""
    return ROUTER_SYSTEM_TEMPLATE.format(date_info=date_info)


def build_intent_user_prompt(query: str, ctx_or_history: Any = "") -> str:
    """Formate la requête avec l'historique récent pour un routage conscient du contexte."""
    if hasattr(ctx_or_history, "history_block"):
        history = getattr(ctx_or_history, "history_block", "")
    else:
        history = str(ctx_or_history)

    history = history.strip()
    if history:
        return f"Historique de la conversation :\n{history}\n\nDemande utilisateur :\n\"{query.strip()}\""
    return f"Demande utilisateur : \"{query.strip()}\""
