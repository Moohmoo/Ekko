"""Interactive terminal REPL adapter driving Ekko conversations."""

import asyncio
from ekko.core.engine import EkkoEngine
from ekko.core.errors import EkkoError
from ekko.memory.in_memory import InMemoryMemory
from ekko.providers.router import LLMRouter
from ekko.settings import Settings
from ekko.tools.registry import ToolRegistry
from ekko.tools.system_info import SystemInfoTool
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


def main() -> None:
    """Bootstrap dependencies and run CLI application."""
    settings = Settings()
    setup_logger(settings)
    provider = LLMRouter(settings=settings).get_provider()
    memory = InMemoryMemory()
    tools = ToolRegistry()
    tools.register(SystemInfoTool())
    engine = EkkoEngine(provider=provider, memory=memory, tools=tools)

    asyncio.run(run_repl(engine))





if __name__ == "__main__":
    main()
