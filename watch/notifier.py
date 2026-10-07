"""Module de notification système Ubuntu pour Ekko.

Déclenche une notification visuelle sur le bureau via l'utilitaire notify-send.
Gère gracieusement les environnements headless ou dépourvus de serveur d'affichage.
"""

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def send_system_notification(
    title: str = "🧠 Veille prête",
    message: str = "Briefing du jour généré",
    icon: str = "utilities-terminal",
) -> bool:
    """Envoie une notification de bureau via notify-send sans bloquer l'exécution."""
    if not shutil.which("notify-send"):
        logger.warning("notify-send n'est pas disponible sur ce système.")
        return False

    cmd = ["notify-send", title, message, f"--icon={icon}"]
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, timeout=5.0)
        return res.returncode == 0
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("Impossible d'afficher la notification système : %s", exc)
        return False
