"""Pydantic schemas for core prompt, user context, and plugins configuration."""

from pydantic import BaseModel, Field


class CorePromptConfig(BaseModel):
    """Global system identity, overarching mission, and behavioral guardrails."""

    identity: str = Field(
        default="You are Ekko, a modular agentic OS assistant.",
        description="Core persona and identity of the agent",
    )
    mission: str = Field(
        default="Execute user requests reliably, leveraging tools when necessary.",
        description="Primary purpose and overarching goals",
    )
    guardrails: list[str] = Field(
        default_factory=lambda: [
            "Be precise, helpful, and concise.",
            "Prioritize local-first execution and resource efficiency.",
        ],
        description="Non-negotiable constraints and safety guidelines",
    )


class UserContextConfig(BaseModel):
    """User-specific settings and preferences decoupled from source code."""

    user_name: str | None = Field(default=None, description="Preferred user display name")
    preferred_language: str = Field(default="fr", description="Primary interaction language")
    preferences: list[str] = Field(
        default_factory=list,
        description="User habits, preferences, and environment facts",
    )
    custom_instructions: str | None = Field(
        default=None,
        description="Specific instructions provided by the user",
    )


class PluginsConfig(BaseModel):
    """Feature flags determining which tools are active in the agent."""

    enabled_tools: list[str] = Field(
        default_factory=lambda: ["system_info"],
        description="List of tool names permitted for agent execution",
    )
