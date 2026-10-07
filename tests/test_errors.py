"""Tests unitaires pour l'entonnoir et la hiérarchie des erreurs (Error Funnel)."""

from core.errors import (
    EkkoError,
    ProviderAuthError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    classify_generic_exception,
    format_error_for_display,
)


def test_error_hierarchy() -> None:
    """Vérifie l'héritage de base des exceptions métier."""
    err = ProviderUnavailableError("Serveur saturé", technical_details="503")
    assert isinstance(err, Exception)
    assert err.user_message == "Serveur saturé"
    assert err.technical_details == "503"


def test_classify_generic_exception_503() -> None:
    """Vérifie la classification d'une erreur 503 en ProviderUnavailableError."""
    exc = Exception("503 UNAVAILABLE. This model is currently experiencing high demand.")
    classified = classify_generic_exception(exc)
    assert isinstance(classified, ProviderUnavailableError)
    assert "saturés" in classified.user_message
    assert "503" in str(classified.technical_details)


def test_classify_generic_exception_timeout() -> None:
    """Vérifie la classification d'un dépassement de délai en ProviderTimeoutError."""
    exc = TimeoutError("Deadline expired before operation could complete.")
    classified = classify_generic_exception(exc)
    assert isinstance(classified, ProviderTimeoutError)
    assert "délai" in classified.user_message


def test_classify_generic_exception_auth() -> None:
    """Vérifie la classification d'une erreur d'authentification en ProviderAuthError."""
    exc = ValueError("API_KEY_INVALID: 401 Unauthorized")
    classified = classify_generic_exception(exc)
    assert isinstance(classified, ProviderAuthError)
    assert "authentification" in classified.user_message


def test_format_error_display_standard() -> None:
    """Vérifie que le mode standard n'affiche que le message utilisateur sobre."""
    err = ProviderUnavailableError("Serveur indisponible", technical_details="Trace interne")
    display = format_error_for_display(err, debug=False)
    assert display == "Serveur indisponible"
    assert "Trace interne" not in display


def test_format_error_display_debug() -> None:
    """Vérifie que le mode debug enrichit le message avec les métadonnées techniques."""
    err = ProviderUnavailableError("Serveur indisponible", technical_details="HTTP 503 code")
    display = format_error_for_display(err, debug=True)
    assert "Serveur indisponible" in display
    assert "ProviderUnavailableError" in display
    assert "HTTP 503 code" in display
