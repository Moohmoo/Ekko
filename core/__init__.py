"""Package central définissant le socle technique transverse d'Ekko."""

from .logger import Logger, setup_logging
from .errors import (
    EkkoError,
    ProviderAuthError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    format_error_for_display,
)

__all__ = [
    "Logger",
    "setup_logging",
    "EkkoError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderAuthError",
    "format_error_for_display",
]
