"""Point d'entrée interactif de l'assistant Ekko (Interface Terminal style agy).

Lance directement la session interactive avec option de débogage (-d / --debug).
"""

import argparse
import asyncio
from config import get_settings
from core import EkkoEngine, SQLiteMemory, load_user_profile
from providers import create_llm_provider
from tools import default_registry
from ui import AgentUI, console, print_banner, render_error, render_final_answer


def parse_args() -> argparse.Namespace:
    """Analyse les options de ligne de commande passées à ekko."""
    parser = argparse.ArgumentParser(description="Ekko - Assistant Personnel Local")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Active le mode verbeux (affiche les prompts, thoughts et JSON bruts)",
    )
    return parser.parse_args()


def initialize_engine() -> EkkoEngine:
    """Initialise et configure le moteur ReAct avec la mémoire et les outils."""
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


async def run_interactive_repl(engine: EkkoEngine, debug: bool = False) -> None:
    """Exécute la boucle interactive principale de l'assistant."""
    settings = get_settings()
    model = settings.gemini_model if settings.llm_provider == "gemini" else settings.local_llm_model
    print_banner(model, settings.llm_provider, debug=debug)

    ui = AgentUI(debug=debug)
    while True:
        try:
            query = console.input("[bold cyan]Ekko > [/bold cyan]").strip()
            if not query:
                continue
            if query.lower() in {"exit", "quit", "q"}:
                console.print("[dim]Au revoir ![/dim]")
                break
            answer = await engine.run(query, callbacks=ui.get_callbacks())
            render_final_answer(answer)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session interrompue. Au revoir ![/dim]")
            break
        except Exception as exc:
            render_error(f"Erreur d'exécution : {exc}")
        finally:
            ui.stop_spinner()


def main() -> None:
    """Point d'entrée principal synchrone."""
    args = parse_args()
    engine = initialize_engine()
    asyncio.run(run_interactive_repl(engine, debug=args.debug))


if __name__ == "__main__":
    main()
