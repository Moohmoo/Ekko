"""Package central définissant le socle technique transverse d'Ekko."""

from .errors import (
    AgentLoopError,
    EkkoError,
    ProviderAuthError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ToolExecutionError,
    format_error_for_display,
)
from .logger import Logger, setup_logging

__all__ = [
    "Logger",
    "setup_logging",
    "EkkoError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderAuthError",
    "ToolExecutionError",
    "AgentLoopError",
    "format_error_for_display",
]
