"""Unit tests for the prompt builder assembling core prompt and user context."""

from ekko.config.schemas import CorePromptConfig, UserContextConfig
from ekko.core.prompt import build_system_prompt


def test_build_system_prompt_basic() -> None:
    """Ensure system prompt renders core identity, mission, and guardrails."""
    core = CorePromptConfig(
        identity="Ekko AI",
        mission="Assist user efficiently",
        guardrails=["No hallucinations", "Be concise"],
    )
    user = UserContextConfig()

    prompt = build_system_prompt(core, user)

    assert "# Identity & Mission" in prompt
    assert "Ekko AI" in prompt
    assert "Assist user efficiently" in prompt
    assert "# Guardrails" in prompt
    assert "- No hallucinations" in prompt
    assert "- Be concise" in prompt
    assert "# User Context" in prompt
    assert "Preferred Language: fr" in prompt


def test_build_system_prompt_with_full_user_context() -> None:
    """Ensure all user context attributes are formatted in the resulting prompt."""
    core = CorePromptConfig()
    user = UserContextConfig(
        user_name="Mohamed",
        preferred_language="fr",
        preferences=["Dark mode", "Python only"],
        custom_instructions="Act as a senior software architect",
    )

    prompt = build_system_prompt(core, user)

    assert "User Name: Mohamed" in prompt
    assert "Preferred Language: fr" in prompt
    assert "- Dark mode" in prompt
    assert "- Python only" in prompt
    assert "Custom Instructions: Act as a senior software architect" in prompt
