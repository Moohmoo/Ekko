"""Prompt builder assembling modular context into a unified system prompt."""

from ekko.config.schemas import CorePromptConfig, UserContextConfig


def _render_user_section(user: UserContextConfig) -> list[str]:
    """Format user context preferences and environment facts into markdown."""
    lines = ["# User Context"]
    if user.user_name:
        lines.append(f"- User Name: {user.user_name}")
    lines.append(f"- Preferred Language: {user.preferred_language}")

    if user.preferences:
        lines.append("- Preferences:")
        for pref in user.preferences:
            lines.append(f"  - {pref}")

    if user.custom_instructions:
        lines.append(f"- Custom Instructions: {user.custom_instructions}")

    return lines


def build_system_prompt(
    core: CorePromptConfig,
    user: UserContextConfig,
) -> str:
    """Assemble core guardrails and dynamic user context into unified markdown."""
    sections: list[str] = [
        "# Identity & Mission",
        core.identity,
        core.mission,
        "",
        "# Guardrails",
    ]
    for rail in core.guardrails:
        sections.append(f"- {rail}")

    sections.append("")
    sections.extend(_render_user_section(user))
    return "\n".join(sections)


def build_default_system_prompt() -> str:
    """Provide minimal baseline system prompt for standalone execution and testing."""
    return (
        "# Identity & Mission\n"
        "You are Ekko, a personal copilot and thinking companion for knowledge management and discovery. "
        "Be direct, natural, helpful, and concise.\n\n"
        "# Domain Concepts\n"
        "- 'echo' (or note, summary): a distilled knowledge note in your vault.\n"
        "- 'signal' (or inbox, feed, news): raw incoming information awaiting triage.\n\n"
        "# Guardrails\n"
        "- Answer plainly without unnecessary technical jargon or rigid self-descriptions.\n"
        "- Provide concise, accurate responses.\n"
        "- Execute appropriate tools when external actions or data lookups are requested.\n"
        "- Strict Tool Grounding: Never hallucinate or invent search results, facts, file contents, or system metrics. "
        "If an action or lookup can be performed by an available tool ('system_info', 'query_knowledge', 'get_recent_notes', 'read_resource', 'scan_inbox'), "
        "you MUST invoke the tool rather than explaining how to perform it manually or fabricating answers.\n"
        "- Gestion stricte des échecs d'outils : Si le message d'un outil commence par [ÉCHEC OUTIL], tu DOIS impérativement reconnaître et expliquer l'échec à l'utilisateur. Il est STRICTEMENT INTERDIT d'affirmer qu'une action a réussi si l'outil a retourné une erreur ou un échec."
    )


