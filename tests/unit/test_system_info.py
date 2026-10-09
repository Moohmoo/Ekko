"""Unit tests for SystemInfoTool inspecting hardware resources and OS metrics."""

from unittest.mock import patch
import pytest

from ekko.core.models import ToolResult
from ekko.core.ports import ToolPort
from ekko.tools.system_info import (
    SystemInfoArgs,
    SystemInfoTool,
    _get_cpu_info,
    _get_disk_info,
    _get_gpu_info,
    _get_memory_info,
    _get_os_info,
)


def test_system_info_tool_complies_with_tool_port() -> None:
    """Ensure SystemInfoTool satisfies ToolPort contract."""
    tool = SystemInfoTool()
    assert isinstance(tool, ToolPort)
    assert tool.name == "system_info"

    schema = tool.get_schema()
    assert schema["function"]["name"] == "system_info"
    assert "parameters" in schema["function"]


def test_os_and_cpu_info_extraction() -> None:
    """Ensure OS and CPU extract non-empty platform details."""
    os_info = _get_os_info()
    cpu_info = _get_cpu_info()

    assert "os" in os_info
    assert "kernel" in os_info
    assert "arch" in cpu_info
    assert cpu_info["cores"] >= 1


def test_disk_info_returns_positive_numbers() -> None:
    """Ensure disk info returns valid storage size strings."""
    disk = _get_disk_info("/")
    assert "total_gb" in disk
    assert "free_gb" in disk
    assert disk["total_gb"] > 0


def test_memory_info_fallback_when_proc_meminfo_unavailable() -> None:
    """Ensure memory info handles missing /proc/meminfo gracefully."""
    with patch("pathlib.Path.exists", return_value=False):
        mem = _get_memory_info()
        assert "total_gb" in mem
        assert "available_gb" in mem


def test_gpu_info_fallback_when_nvidia_smi_absent() -> None:
    """Ensure GPU detection returns fallback note when nvidia-smi is missing."""
    with patch("shutil.which", return_value=None):
        gpus = _get_gpu_info()
        assert len(gpus) == 1
        assert "No NVIDIA GPU" in gpus[0]


@pytest.mark.asyncio
async def test_system_info_execute_returns_valid_tool_result() -> None:
    """Ensure executing the tool yields successful ToolResult with all metrics."""
    tool = SystemInfoTool()
    result = await tool.execute()

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert "Operating System" in result.content
    assert "CPU" in result.content
    assert "Memory (RAM)" in result.content
    assert "Disk" in result.content
