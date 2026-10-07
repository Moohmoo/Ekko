"""Point d'entrée interactif de l'assistant Ekko (Interface Terminal style agy).

Permet d'exécuter l'agent en mode commande unique ou en boucle REPL interactive.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from config import get_settings
from core import EkkoEngine, SQLiteMemory, load_user_profile
from providers import create_llm_provider
from tools import default_registry
from ui import (
    console,
    print_banner,
    render_error,
    render_final_answer,
    render_thought,
    render_tool_call,
    render_tool_result,
)


def get_callbacks() -> dict[str, Any]:
    """Retourne le mapping des callbacks graphiques Rich pour le moteur ReAct."""
    return {
        "on_thought": render_thought,
        "on_tool_call": render_tool_call,
        "on_tool_result": render_tool_result,
    }


def parse_args() -> argparse.Namespace:
    """Analyse les arguments passés à la commande ekko."""
    parser = argparse.ArgumentParser(description="Ekko - Assistant Personnel Local")
    parser.add_argument("query", nargs="*", help="Requête directe à exécuter (mode one-shot)")
    return parser.parse_args()


def initialize_engine() -> EkkoEngine:
    """Initialise et configure le moteur avec la configuration active."""
    settings = get_settings()
    provider = create_llm_provider(settings)
    memory_db = settings.memory_dir_path / "ekko.db"
    memory = SQLiteMemory(memory_db)
    user_profile = load_user_profile(settings.memory_dir_path)

    return EkkoEngine(
        settings=settings,
        provider=provider,
        registry=default_registry,
        memory=memory,
        user_profile=user_profile,
    )


async def run_interactive_repl(engine: EkkoEngine) -> None:
    """Lance la boucle interactive en invite de commande."""
    settings = get_settings()
    model_name = settings.gemini_model if settings.llm_provider == "gemini" else settings.local_llm_model
    print_banner(model_name, settings.llm_provider)

    callbacks = get_callbacks()
    while True:
        try:
            query = console.input("[bold cyan]Ekko > [/bold cyan]").strip()
            if not query:
                continue
            if query.lower() in {"exit", "quit", "q"}:
                console.print("[dim]Au revoir ![/dim]")
                break

            answer = await engine.run(query, callbacks=callbacks)
            render_final_answer(answer)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Interruption détectée. Au revoir ![/dim]")
            break
        except Exception as exc:
            render_error(f"Une erreur est survenue : {exc}")


async def run_single_query(engine: EkkoEngine, query: str) -> None:
    """Exécute une requête unique transmise en ligne de commande."""
    try:
        answer = await engine.run(query, callbacks=get_callbacks())
        render_final_answer(answer)
    except Exception as exc:
        render_error(f"Erreur d'exécution : {exc}")


def main() -> None:
    """Point d'entrée principal synchrone."""
    args = parse_args()
    engine = initialize_engine()
    raw_query = " ".join(args.query).strip()

    if raw_query:
        asyncio.run(run_single_query(engine, raw_query))
    else:
        asyncio.run(run_interactive_repl(engine))


if __name__ == "__main__":
    main()
