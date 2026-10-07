"""Tests unitaires pour le module des prompts core/prompts.py."""

from agent.prompts import build_system_prompt, format_history_block, format_step_prompt


def test_build_system_prompt_interpolation() -> None:
    """Vérifie l'injection correcte du profil utilisateur et du catalogue."""
    prompt = build_system_prompt(
        user_profile="Profil Ingenieur",
        tools_catalog="- run_daily_watch : Veille tech",
    )
    assert "Profil Ingenieur" in prompt
    assert "- run_daily_watch : Veille tech" in prompt
    assert "EXEMPLES DE DÉCISION" in prompt
    assert "run_daily_watch" in prompt


def test_format_history_block_empty() -> None:
    """Vérifie qu'un historique vide retourne une chaîne vide."""
    assert format_history_block([]) == ""


def test_format_history_block_content() -> None:
    """Vérifie le formatage structuré des messages d'historique."""
    history = [
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Réponse 1"},
    ]
    block = format_history_block(history)
    assert "### HISTORIQUE CONVERSATIONNEL RÉCENT :" in block
    assert "- Utilisateur : Question 1" in block
    assert "- Ekko : Réponse 1" in block


def test_format_step_prompt() -> None:
    """Vérifie l'assemblage de la demande et des observations."""
    prompt = format_step_prompt(
        user_query="Donne les news",
        observations=["- Résultat de run_daily_watch : Briefing prêt"],
        history_block="### HISTORIQUE",
    )
    assert "### HISTORIQUE" in prompt
    assert "Demande utilisateur : Donne les news" in prompt
    assert "Observations des outils précédents" in prompt
    assert "- Résultat de run_daily_watch : Briefing prêt" in prompt
