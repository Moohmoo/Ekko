"""Domain exception hierarchy for Ekko."""


class EkkoError(Exception):
    """Base exception for all domain-level errors in Ekko."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class ProviderError(EkkoError):
    """Raised when an external LLM provider fails or returns invalid output."""

    pass
