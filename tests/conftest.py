"""Configuration pytest et fixtures partagées pour Ekko."""

import sys
from pathlib import Path

# Ajoute la racine du projet Ekko au PYTHONPATH pour les imports directs
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
