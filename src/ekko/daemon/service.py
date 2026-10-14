"""Unified daemon composition root coordinating background ingestion, IPC server, and resource confinement."""

import argparse
import asyncio
from pathlib import Path
import signal
from typing import Any

from ekko.daemon.resources import ResourceManager
from ekko.daemon.scheduler import IngestionCoordinator
from ekko.daemon.server import DEFAULT_SOCKET_PATH, IPCServer
from ekko.db.embedder import TextEmbedder
from ekko.db.manager import DatabaseManager
from ekko.domains.ingestion.distiller import SignalDistiller
from ekko.logger import get_logger, setup_logger
from ekko.providers.router import LLMRouter
from ekko.settings import Settings

logger = get_logger("daemon.service")


def _setup_signal_handlers(loop: asyncio.AbstractEventLoop, stop_event: asyncio.Event) -> None:
    """Register SIGINT and SIGTERM handlers to set stop_event."""
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass


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


def _compose_coordinator(
    settings: Settings,
    store: DatabaseManager,
    embedder: TextEmbedder | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> IngestionCoordinator:
    """Create IngestionCoordinator wired with shared embedder and semaphore."""
    provider = LLMRouter(settings=settings).get_provider()
    notes_dir = getattr(settings, "notes_dir", "data/notes")
    distiller = SignalDistiller(
        store=store,
        llm_provider=provider,
        notes_dir=notes_dir,
        embedder=embedder,
        semaphore=semaphore,
    )
    return IngestionCoordinator(
        db_manager=store,
        config_dir=settings.config_dir,
        distiller=distiller,
        auto_distill=False,
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
    embedder = TextEmbedder()
    inference_semaphore = asyncio.Semaphore(1)

    store = DatabaseManager(db_path=active_settings.sqlite_db_path)
    coordinator = _compose_coordinator(
        active_settings,
        store,
        embedder=embedder,
        semaphore=inference_semaphore,
    )

    sock = Path(socket_path or getattr(active_settings, "ipc_socket_path", DEFAULT_SOCKET_PATH))
    server = IPCServer(
        socket_path=sock,
        db_manager=store,
        distiller=coordinator.distiller,
        distillation_semaphore=inference_semaphore,
        embedder=embedder,
        coordinator=coordinator,
        settings=active_settings,
    )

    evt = stop_event or asyncio.Event()
    if stop_event is None:
        _setup_signal_handlers(asyncio.get_running_loop(), evt)

    await _run_services(coordinator, server, evt, poll_interval)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for daemon subcommand and options."""
    parser = argparse.ArgumentParser(description="Ekko Ambient Daemon")
    subparsers = parser.add_subparsers(dest="command")

    daemon_parser = subparsers.add_parser("daemon", help="Run Ekko background daemon and IPC server")
    daemon_parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Polling interval in seconds (default: 60.0)",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Polling interval in seconds (default: 60.0)",
    )
    return parser.parse_args(args)


def main(argv: list[str] | None = None) -> None:
    """Main CLI entrypoint launching the daemon directly."""
    parsed = parse_args(argv)
    interval = getattr(parsed, "interval", 60.0)
    asyncio.run(run_daemon(poll_interval=interval))


if __name__ == "__main__":
    main()
