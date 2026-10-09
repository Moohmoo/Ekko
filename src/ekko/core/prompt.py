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
