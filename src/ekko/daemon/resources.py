"""Resource management for process priority confinement and VRAM unloading."""

import os
from typing import Any
from ekko.utils.logger import get_logger

logger = get_logger("daemon.resources")


class ResourceManager:
    """Manages daemon host resource etiquette and GPU memory cleanup."""

    def apply_process_niceness(self, increment: int = 10) -> int:
        """Lower daemon CPU scheduling priority using POSIX niceness safely."""
        try:
            current_nice = os.nice(increment)
            logger.info("Daemon process priority lowered with niceness increment +%d (level: %d)", increment, current_nice)
            return current_nice
        except (AttributeError, PermissionError, OSError) as exc:
            logger.warning("Could not adjust process niceness (%s). Proceeding with normal priority.", exc)
            return 0

    def inject_unload_vram(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Inject keep_alive: 0 parameter to instruct Ollama/LiteLLM to unload VRAM immediately."""
        merged = dict(params or {})
        extra = dict(merged.get("extra_body") or {})
        extra["keep_alive"] = 0
        merged["extra_body"] = extra
        return merged
