"""Main asynchronous terminal application coordinating input, streaming, and rendering."""

import argparse
import asyncio
from pathlib import Path
from typing import Any

from ekko.config.loader import (
    load_core_prompt,
    load_plugins_config,
    load_user_context,
)
from ekko.core.engine import EkkoEngine
from ekko.core.prompt import build_system_prompt
from ekko.memory.hybrid_store import HybridStore
from ekko.memory.sqlite_memory import SqliteMemory
from ekko.providers.router import LLMRouter
from ekko.settings import Settings
from ekko.tools.catalog import ToolCatalog
from ekko.cli.input import CLIInputHandler, CommandType, ToolbarMetadata
from ekko.cli.renderer import CLIRenderer
from ekko.logger import setup_logger


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for target session, daemon subcommand and flags."""
    parser = argparse.ArgumentParser(description="Ekko Modern CLI")
    subparsers = parser.add_subparsers(dest="command")

    daemon_parser = subparsers.add_parser("daemon", help="Run Ekko background daemon and IPC server")
    daemon_parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Polling interval in seconds (default: 60.0)",
    )

    parser.add_argument(
        "--session",
        "-s",
        type=str,
        default="default",
        help="Session identifier to load or persist (default: default)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing history for the target session before starting",
    )
    return parser.parse_args(args)


async def _stream_turn(
    engine: EkkoEngine,
    renderer: CLIRenderer,
    text: str,
    session_id: str,
) -> None:
    """Stream single turn events to renderer and capture interruptions."""
    try:
        async for event in engine.run_stream(text, session_id=session_id):
            renderer.render_event(event)
    except KeyboardInterrupt:
        renderer._stop_status()
        renderer.console.print("\n[yellow]Génération interrompue par l'utilisateur.[/]")


async def run_app(
    engine: EkkoEngine,
    memory: Any,
    input_handler: CLIInputHandler | None = None,
    renderer: CLIRenderer | None = None,
    metadata: ToolbarMetadata | None = None,
    session_id: str = "default",
    clear: bool = False,
) -> None:
    """Run interactive REPL loop coordinating prompt session and event rendering."""
    active_metadata = metadata or ToolbarMetadata(session_id=session_id, workspace=str(Path.cwd()))
    active_input = input_handler or CLIInputHandler(metadata=active_metadata)
    active_renderer = renderer or CLIRenderer()

    if clear:
        await memory.clear_session(session_id)
        active_renderer.render_clear(session_id)

    active_renderer.render_home(active_metadata)

    while True:
        user_input = await active_input.get_input()
        if user_input.command == CommandType.EXIT:
            active_renderer.render_exit()
            break
        if user_input.command == CommandType.CLEAR:
            await memory.clear_session(session_id)
            active_renderer.render_clear(session_id)
            continue
        if user_input.command == CommandType.HELP:
            active_renderer.render_help()
            continue
        if user_input.command == CommandType.INTERRUPT:
            continue
        if user_input.command == CommandType.USER_PROMPT:
            if not user_input.text:
                continue
            await _stream_turn(engine, active_renderer, user_input.text, session_id)


def main(argv: list[str] | None = None) -> None:
    """Bootstrap application settings, dependencies, and launch modern REPL or daemon."""
    parsed = parse_args(argv)
    if getattr(parsed, "command", None) == "daemon":
        # Permitted CLI router lazy-load: prevent loading full background daemon stack during REPL startup
        from ekko.daemon.service import run_daemon

        asyncio.run(run_daemon(poll_interval=parsed.interval))
        return

    settings = Settings()
    setup_logger(settings)

    core_prompt = load_core_prompt(settings.config_dir)
    user_context = load_user_context(settings.config_dir)
    plugins_config = load_plugins_config(settings.config_dir)

    system_prompt = build_system_prompt(core_prompt, user_context)
    db_manager = HybridStore(db_path=settings.sqlite_db_path)
    catalog = ToolCatalog(include_defaults=True)
    tools = catalog.build_registry(plugins_config.enabled_tools, db_manager=db_manager)

    provider = LLMRouter(settings=settings).get_provider()
    memory = SqliteMemory(db_path=settings.sqlite_db_path)
    engine = EkkoEngine(
        provider=provider,
        memory=memory,
        tools=tools,
        system_prompt=system_prompt,
    )

    model_name = getattr(provider, "model", None) or settings.active_model
    metadata = ToolbarMetadata(
        model_name=model_name,
        session_id=parsed.session,
        workspace=str(Path.cwd()),
    )


    asyncio.run(
        run_app(
            engine=engine,
            memory=memory,
            metadata=metadata,
            session_id=parsed.session,
            clear=parsed.clear,
        )
    )


if __name__ == "__main__":
    main()
