"""Interactive terminal REPL adapter driving Ekko conversations."""

import argparse
import asyncio
import inspect
from ekko.config.loader import (
    load_core_prompt,
    load_plugins_config,
    load_user_context,
)
from ekko.core.engine import EkkoEngine
from ekko.core.errors import EkkoError
from ekko.core.prompt import build_system_prompt
from ekko.memory.sqlite_memory import SqliteMemory
from ekko.providers.router import LLMRouter
from ekko.settings import Settings
from ekko.tools.catalog import ToolCatalog
from ekko.utils.logger import setup_logger

EXIT_COMMANDS = {"exit", "quit", "q", "/exit", "/quit"}


def _is_exit_command(text: str) -> bool:
    """Check if the user issued a command to leave the session."""
    return text.strip().lower() in EXIT_COMMANDS


async def _handle_turn(
    engine: EkkoEngine,
    user_input: str,
    session_id: str,
) -> None:
    """Execute a single engine turn and print result or domain error."""
    try:
        reply = await engine.process_message(user_input, session_id=session_id)
        print(f"Ekko: {reply}\n")
    except EkkoError as err:
        print(f"Error: {err}\n")
    except ValueError as err:
        print(f"Validation error: {err}\n")


async def run_repl(engine: EkkoEngine, session_id: str = "default") -> None:
    """Main interactive REPL loop reading standard input."""
    print("=== Ekko Agentic OS (CLI) ===")
    print("Type 'exit' or 'quit' to end session.\n")

    while True:
        try:
            user_input = input("You: ")
        except (KeyboardInterrupt, EOFError):
            print("\nSession closed.")
            break

        if _is_exit_command(user_input):
            print("Goodbye!")
            break
        if not user_input.strip():
            continue

        await _handle_turn(engine, user_input, session_id)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for session identifier and flags."""
    parser = argparse.ArgumentParser(description="Ekko Agentic OS CLI")
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


async def _start_cli(
    engine: EkkoEngine,
    memory: SqliteMemory,
    session_id: str,
    clear: bool,
) -> None:
    """Execute pre-session cleanup if requested and start REPL."""
    if clear:
        await memory.clear_session(session_id)
        print(f"Session '{session_id}' cleared.\n")
    turn = run_repl(engine, session_id=session_id)
    if inspect.isawaitable(turn):
        await turn


def main(argv: list[str] | None = None) -> None:
    """Bootstrap dependencies, load contexts, and run CLI application."""
    parsed = parse_args(argv)
    settings = Settings()
    setup_logger(settings)

    core_prompt = load_core_prompt(settings.config_dir)
    user_context = load_user_context(settings.config_dir)
    plugins_config = load_plugins_config(settings.config_dir)

    system_prompt = build_system_prompt(core_prompt, user_context)
    catalog = ToolCatalog(include_defaults=True)
    tools = catalog.build_registry(plugins_config.enabled_tools)

    provider = LLMRouter(settings=settings).get_provider()
    memory = SqliteMemory(db_path=settings.sqlite_db_path)
    engine = EkkoEngine(
        provider=provider,
        memory=memory,
        tools=tools,
        system_prompt=system_prompt,
    )

    asyncio.run(_start_cli(engine, memory, parsed.session, parsed.clear))


if __name__ == "__main__":
    main()

