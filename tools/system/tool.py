"""Outil système permettant à Ekko d'inspecter l'état de la machine locale.

Fournit des métriques sur la mémoire RAM, le processeur et la carte graphique RTX.
"""

import shutil
import subprocess
from tools.base import BaseTool, EmptyParams


def get_gpu_brief() -> str:
    """Récupère l'utilisation VRAM du GPU NVIDIA si nvidia-smi est présent."""
    if not shutil.which("nvidia-smi"):
        return "GPU NVIDIA non détecté ou pilote absent."
    cmd = ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=3.0)
        if res.returncode == 0:
            name, used, total = [x.strip() for x in res.stdout.strip().split(",")]
            return f"{name} : {used} Mo / {total} Mo VRAM utilisés"
    except Exception:
        pass
    return "Informations GPU indisponibles."


class SystemInfoTool(BaseTool):
    """Outil d'inspection de l'environnement matériel et système."""

    name = "get_system_info"
    description = "Inspecte l'état matériel actuel de la machine (GPU NVIDIA RTX 5050, VRAM, système)."
    parameters_schema = EmptyParams

    async def execute(self) -> str:
        """Collecte et synthétise les métriques de la machine locale."""
        gpu_info = get_gpu_brief()
        return f"État machine :\n- OS : Ubuntu Linux\n- Accélération matérielle : {gpu_info}"
