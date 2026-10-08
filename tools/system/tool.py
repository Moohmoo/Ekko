"""Outil système permettant à Ekko d'inspecter l'état de la machine locale.

Fournit des métriques sur le système d'exploitation et la carte graphique NVIDIA.
"""

import asyncio
import platform
import shutil
import subprocess
from tools.base import BaseTool, EmptyParams


def get_gpu_brief() -> str:
    """Récupère l'utilisation VRAM du ou des GPUs NVIDIA si nvidia-smi est présent."""
    if not shutil.which("nvidia-smi"):
        return "GPU NVIDIA non détecté ou pilote absent."
    cmd = ["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=3.0)
        if res.returncode == 0:
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
            gpu_reports: list[str] = []
            for line in lines:
                parts = [x.strip() for x in line.split(",")]
                if len(parts) >= 3:
                    gpu_reports.append(f"{parts[0]} : {parts[1]} Mo / {parts[2]} Mo VRAM")
            if gpu_reports:
                return " | ".join(gpu_reports)
    except Exception:
        pass
    return "Informations GPU indisponibles."


class SystemInfoTool(BaseTool):
    """Outil d'inspection de l'environnement matériel et système."""

    name = "get_system_info"
    description = "Inspecte l'état matériel et logiciel de la machine hôte (GPU, VRAM, système d'exploitation)."
    parameters_schema = EmptyParams

    async def execute(self) -> str:
        """Collecte et synthétise les métriques de la machine locale."""
        os_info = f"{platform.system()} {platform.release()}"
        gpu_info = await asyncio.to_thread(get_gpu_brief)
        return f"État machine :\n- OS : {os_info}\n- Accélération matérielle : {gpu_info}"
