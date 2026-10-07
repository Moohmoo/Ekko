"""Exceptions typées pour les fournisseurs de modèles LLM."""


class ProviderError(Exception):
    """Exception racine pour les défaillances des fournisseurs LLM."""

    def __init__(self, user_message: str, technical_details: str | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_details = technical_details


class ProviderUnavailableError(ProviderError):
    """Fournisseur LLM temporairement saturé ou indisponible (ex: HTTP 503)."""


class ProviderTimeoutError(ProviderError, TimeoutError):
    """Dépassement du délai de réponse imparti auprès du fournisseur (ex: HTTP 504)."""


class ProviderAuthError(ProviderError):
    """Erreur d'authentification ou clé d'API invalide (ex: HTTP 401/403)."""
