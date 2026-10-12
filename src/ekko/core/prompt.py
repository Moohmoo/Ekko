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
        "You are Ekko, a modular agentic OS assistant. Be precise, helpful, and concise.\n\n"
        "# Guardrails\n"
        "- Provide concise, accurate responses.\n"
        "- Execute appropriate tools when external actions or data lookups are requested."
    )
