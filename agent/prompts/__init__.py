"""Package centralisant l'intégralité des prompts et gabarits de l'agent Ekko."""

from .action import (
    SYSTEM_PROMPT_TEMPLATE,
    build_system_prompt,
    format_history_block,
    format_step_prompt,
)
from .chat import CHAT_SYSTEM_TEMPLATE, build_chat_prompt
from .default_profile import DEFAULT_PROFILE_CONTENT
from .research import (
    RESEARCH_PLANNER_TEMPLATE,
    SYNTHESIZER_SYSTEM_TEMPLATE,
    build_research_planner_prompt,
    build_synthesis_prompt,
)
from .router import (
    ROUTER_SYSTEM_TEMPLATE,
    build_intent_prompt,
    build_intent_user_prompt,
)
from .validator import (
    VALIDATOR_SYSTEM_PROMPT,
    build_validator_prompt,
    format_validation_prompt,
)

__all__ = [
    "DEFAULT_PROFILE_CONTENT",
    "CHAT_SYSTEM_TEMPLATE",
    "build_chat_prompt",
    "ROUTER_SYSTEM_TEMPLATE",
    "build_intent_prompt",
    "build_intent_user_prompt",
    "RESEARCH_PLANNER_TEMPLATE",
    "SYNTHESIZER_SYSTEM_TEMPLATE",
    "build_research_planner_prompt",
    "build_synthesis_prompt",
    "SYSTEM_PROMPT_TEMPLATE",
    "build_system_prompt",
    "format_history_block",
    "format_step_prompt",
    "VALIDATOR_SYSTEM_PROMPT",
    "build_validator_prompt",
    "format_validation_prompt",
]
