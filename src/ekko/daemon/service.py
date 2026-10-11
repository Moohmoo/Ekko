"""Unified daemon composition root coordinating background ingestion, IPC server, and resource confinement."""

import asyncio
from pathlib import Path
import signal

from ekko.config.loader import load_core_prompt, load_plugins_config, load_user_context
from ekko.core.engine import EkkoEngine
from ekko.core.prompt import build_system_prompt
from ekko.daemon.distiller import SignalDistiller
from ekko.daemon.resources import ResourceManager
from ekko.daemon.scheduler import IngestionCoordinator
from ekko.daemon.server import DEFAULT_SOCKET_PATH, IPCServer
from ekko.logger import get_logger, setup_logger
from ekko.memory.hybrid_store import HybridStore
from ekko.memory.sqlite_memory import SqliteMemory
from ekko.providers.router import LLMRouter
from ekko.settings import Settings
from ekko.tools.catalog import ToolCatalog

logger = get_logger("daemon.service")


def _setup_signal_handlers(loop: asyncio.AbstractEventLoop, stop_event: asyncio.Event) -> None:
    """Register SIGINT and SIGTERM handlers to set stop_event."""
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass


def _build_engine(settings: Settings, store: HybridStore) -> EkkoEngine:
    """Compose and return an EkkoEngine instance for IPC prompt execution."""
    core_prompt = load_core_prompt(settings.config_dir)
    user_context = load_user_context(settings.config_dir)
    plugins_config = load_plugins_config(settings.config_dir)
    system_prompt = build_system_prompt(core_prompt, user_context)

    catalog = ToolCatalog(include_defaults=True)
    tools = catalog.build_registry(plugins_config.enabled_tools, db_manager=store)
    provider = LLMRouter(settings=settings).get_provider()
    memory = SqliteMemory(db_path=settings.sqlite_db_path)
    return EkkoEngine(
        provider=provider,
        memory=memory,
        tools=tools,
        system_prompt=system_prompt,
    )


async def _run_services(
    coordinator: IngestionCoordinator,
    server: IPCServer,
    stop_event: asyncio.Event,
    poll_interval: float,
) -> None:
    """Start services and await stop_event before graceful teardown."""
    await coordinator.start(poll_interval_seconds=poll_interval)
    await server.start()
    logger.info("Daemon active on %s. Waiting for shutdown signal.", server.socket_path)
    try:
        await stop_event.wait()
    finally:
        logger.info("Stopping daemon components...")
        await coordinator.stop()
        await server.stop()
        logger.info("Daemon components cleanly stopped.")


def _compose_coordinator(settings: Settings, store: HybridStore) -> IngestionCoordinator:
    """Create IngestionCoordinator wired with autonomous SignalDistiller."""
    provider = LLMRouter(settings=settings).get_provider()
    notes_dir = getattr(settings, "notes_dir", "data/notes")
    distiller = SignalDistiller(store=store, llm_provider=provider, notes_dir=notes_dir)
    return IngestionCoordinator(
        db_manager=store,
        config_dir=settings.config_dir,
        distiller=distiller,
    )


async def run_daemon(
    settings: Settings | None = None,
    socket_path: Path | str | None = None,
    poll_interval: float = 60.0,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Initialize and run daemon services until shutdown signal."""
    active_settings = settings or Settings()
    setup_logger(active_settings)

    ResourceManager().apply_process_niceness(increment=10)
    store = HybridStore(db_path=active_settings.sqlite_db_path)
    engine = _build_engine(active_settings, store)
    coordinator = _compose_coordinator(active_settings, store)

    sock = Path(socket_path or getattr(active_settings, "ipc_socket_path", DEFAULT_SOCKET_PATH))
    server = IPCServer(
        socket_path=sock,
        db_manager=store,
        engine=engine,
        distiller=coordinator.distiller,
    )

    evt = stop_event or asyncio.Event()
    if stop_event is None:
        _setup_signal_handlers(asyncio.get_running_loop(), evt)

    await _run_services(coordinator, server, evt, poll_interval)


if __name__ == "__main__":
    asyncio.run(run_daemon())
