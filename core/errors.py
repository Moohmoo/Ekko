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


def _get_remediation_action(error: Exception) -> str:
    """Fournit un conseil d'action immédiat selon la nature de l'erreur."""
    if isinstance(error, ProviderUnavailableError):
        return "Attendez 30-60s (pic de charge temporaire chez Google) ou basculez en modèle local."
    if isinstance(error, ProviderTimeoutError):
        return "Le serveur distant tarde à répondre. Vérifiez votre accès réseau ou réessayez."
    if isinstance(error, ProviderAuthError):
        return "Vérifiez que GEMINI_API_KEY est correctement renseignée dans votre fichier .env."
    if isinstance(error, ToolExecutionError):
        return "Vérifiez les prérequis matériels ou les autorisations système de l'outil."
    return "Consultez les détails dans data/logs/ekko.log ou réessayez avec une requête reformulée."


def format_error_for_display(exc: Exception, debug: bool = False) -> str:
    """Entonnoir central formatant l'erreur pour l'affichage terminal."""
    error = exc if isinstance(exc, (EkkoError, ProviderError)) else classify_generic_exception(exc)
    tech = getattr(error, "technical_details", None) or str(exc)
    user_msg = getattr(error, "user_message", None) or str(exc)
    logger.error("Erreur interceptée par l'entonnoir: %s", tech)

    if not debug:
        return user_msg

    action = _get_remediation_action(error)
    return (
        f"{user_msg}\n\n"
        f"[dim]Type : {type(error).__name__}[/dim]\n"
        f"[dim]Diagnostic : {tech}[/dim]\n"
        f"[cyan]Action : {action}[/cyan]\n"
        f"[dim]Logs : data/logs/ekko.log[/dim]"
    )
