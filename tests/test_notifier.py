"""Tests unitaires pour le module de notification système."""

from unittest.mock import patch
from watch.notifier import send_system_notification


def test_notifier_missing_binary() -> None:
    """Vérifie que l'absence de notify-send renvoie False sans lever d'exception."""
    with patch("shutil.which", return_value=None):
        result = send_system_notification("Titre", "Message")
        assert result is False


def test_notifier_successful_call() -> None:
    """Vérifie l'exécution réussie de notify-send via subprocess simulé."""
    with patch("shutil.which", return_value="/usr/bin/notify-send"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        result = send_system_notification("Titre", "Message")
        assert result is True
        mock_run.assert_called_once()
