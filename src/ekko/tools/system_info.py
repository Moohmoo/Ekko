"""SystemInfoTool inspecting host operating system and hardware resource metrics."""

import os
from pathlib import Path
import platform
import shutil
import subprocess
from pydantic import BaseModel, Field

from ekko.core.models import ToolResult
from ekko.tools.base import BaseTool


class SystemInfoArgs(BaseModel):
    """Schema for system information query (no mandatory parameters)."""

    include_gpu: bool = Field(
        default=True,
        description="Whether to query GPU devices and VRAM via nvidia-smi",
    )


def _get_os_info() -> dict[str, str]:
    """Extract OS name, Linux distribution, and kernel version."""
    distro = platform.system()
    os_release = Path("/etc/os-release")
    if os_release.exists():
        try:
            for line in os_release.read_text(encoding="utf-8").splitlines():
                if line.startswith("PRETTY_NAME="):
                    distro = line.split("=", 1)[1].strip('"')
                    break
        except Exception:
            pass
    return {"os": distro, "kernel": platform.release(), "arch": platform.machine()}


def _get_cpu_info() -> dict[str, str | int]:
    """Extract CPU architecture and core count."""
    return {"arch": platform.machine(), "cores": os.cpu_count() or 1}


def _get_memory_info() -> dict[str, float]:
    """Extract total and available RAM from /proc/meminfo with fallback."""
    meminfo = Path("/proc/meminfo")
    total_kb, avail_kb = 0, 0
    if meminfo.exists():
        try:
            for line in meminfo.read_text(encoding="utf-8").splitlines():
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    avail_kb = int(line.split()[1])
        except Exception:
            pass
    return {
        "total_gb": round(total_kb / (1024 * 1024), 2),
        "available_gb": round(avail_kb / (1024 * 1024), 2),
    }


def _get_disk_info(path: str = "/") -> dict[str, float]:
    """Extract disk space metrics for the specified mount point."""
    try:
        usage = shutil.disk_usage(path)
        return {
            "total_gb": round(usage.total / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
        }
    except Exception:
        return {"total_gb": 0.0, "free_gb": 0.0}


def _get_gpu_info() -> list[str]:
    """Probe GPU devices and VRAM availability via nvidia-smi safely."""
    if not shutil.which("nvidia-smi"):
        return ["No NVIDIA GPU detected (nvidia-smi absent)"]
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.free",
            "--format=csv,noheader,nounits",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2, check=True)
        gpus: list[str] = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if len(parts) >= 3:
                gpus.append(f"{parts[0]} ({parts[2]} MB free / {parts[1]} MB total VRAM)")
        return gpus or ["No GPU reporting via nvidia-smi"]
    except Exception as err:
        return [f"GPU query failed: {err}"]


class SystemInfoTool(BaseTool):
    """Tool inspecting hardware resources, operating system, and GPU/VRAM."""

    name: str = "system_info"
    description: str = (
        "Inspect the LIVE host hardware resources (current CPU %, available RAM, disk space, GPU/VRAM) "
        "of the local machine running Ekko. Do NOT use this tool for project architecture, software benchmarks, "
        "or documented performance metrics in notes."
    )
    args_schema: type[BaseModel] = SystemInfoArgs

    async def _run(self, include_gpu: bool = True) -> ToolResult:
        """Collect system metrics and compile into a structured report."""
        os_info = _get_os_info()
        cpu_info = _get_cpu_info()
        mem_info = _get_memory_info()
        disk_info = _get_disk_info("/")
        gpu_info = _get_gpu_info() if include_gpu else ["GPU check skipped"]

        report = [
            "System Hardware & Resource Status:",
            f"- Operating System: {os_info['os']} (Kernel: {os_info['kernel']}, Arch: {os_info['arch']})",
            f"- CPU: {cpu_info['cores']} logical cores ({cpu_info['arch']})",
            f"- Memory (RAM): {mem_info['available_gb']} GB available / {mem_info['total_gb']} GB total",
            f"- Disk: {disk_info['free_gb']} GB free / {disk_info['total_gb']} GB total",
            f"- GPU: {'; '.join(gpu_info)}",
        ]
        return ToolResult(content="\n".join(report), success=True)
