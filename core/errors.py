"""Entonnoir et hiérarchie centralisée des erreurs d'Ekko.

Catégorise les défaillances (réseau, authentification, outils, boucle agent)
pour produire des diagnostics clairs en mode normal et enrichis en debug.
"""

import logging
from providers.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger("ekko.core.errors")


class EkkoError(Exception):
    """Exception racine pour toutes les erreurs gérées par l'agent."""

    def __init__(self, user_message: str, technical_details: str | None = None) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_details = technical_details


class ToolExecutionError(EkkoError):
    """Signalé lors de la défaillance d'un outil local de l'agent."""


class AgentLoopError(EkkoError):
    """Signalé lorsque la boucle de raisonnement ReAct atteint sa limite."""


def classify_generic_exception(exc: Exception) -> EkkoError | ProviderError:
    """Convertit une exception non typée en une erreur catégorisée d'Ekko."""
    if isinstance(exc, (TimeoutError, TimeoutError)):
        return ProviderTimeoutError(
            "Le serveur distant n'a pas répondu dans le délai imparti.",
            technical_details=str(exc),
        )
    msg = str(exc).lower()
    if "503" in msg or "high demand" in msg or "unavailable" in msg:
        return ProviderUnavailableError(
            "Les serveurs Google Gemini sont actuellement saturés (forte affluence).",
            technical_details=str(exc),
        )
    if "504" in msg or "deadline_exceeded" in msg or "timeout" in msg:
        return ProviderTimeoutError(
            "Le serveur distant n'a pas répondu dans le délai imparti.",
            technical_details=str(exc),
        )
    if "401" in msg or "403" in msg or "api_key" in msg:
        return ProviderAuthError(
            "Échec d'authentification auprès du fournisseur LLM (clé API invalide ou absente).",
            technical_details=str(exc),
        )
    return EkkoError(
        f"Une anomalie est survenue : {exc}",
        technical_details=f"Type: {type(exc).__name__} | Exception: {exc}",
    )


def format_error_for_display(exc: Exception, debug: bool = False) -> str:
    """Entonnoir central formatant l'erreur pour l'affichage terminal."""
    error = exc if isinstance(exc, (EkkoError, ProviderError)) else classify_generic_exception(exc)
    logger.error("Erreur interceptée par l'entonnoir: %s", error.technical_details or error.user_message)

    if not debug:
        return error.user_message

    details = error.technical_details or "Aucun détail technique supplémentaire."
    return (
        f"{error.user_message}\n\n"
        f"[dim]Type : {type(error).__name__}[/dim]\n"
        f"[dim]Diagnostic : {details}[/dim]"
    )
