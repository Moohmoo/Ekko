"""Point d'entrée interactif de l'assistant Ekko (Interface Terminal style agy).

Lance directement la session interactive avec option de débogage (-d / --debug).
"""

import argparse
import asyncio
from agent import AgentRequest, EkkoEngine, SQLiteMemory, load_user_profile
from config import Settings, get_settings
from core import format_error_for_display, setup_logging
from providers import create_llm_provider
from ui import (
    AgentUI,
    console,
    print_banner,
    prompt_user_input,
    render_error,
    render_final_answer,
)


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


def initialize_engine(settings: Settings | None = None) -> EkkoEngine:
    """Initialise et configure le moteur ReAct avec la mémoire et les outils."""
    cfg = settings or get_settings()
    provider = create_llm_provider(cfg)
    memory = SQLiteMemory(cfg.db_path)
    user_profile = load_user_profile(cfg.memory_dir_path)

    return EkkoEngine(
        settings=cfg,
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
            query = prompt_user_input()
            if not query:
                continue
            if query.lower() in {"exit", "quit", "q"}:
                console.print("[dim]Au revoir ![/dim]")
                break
            request = AgentRequest(query=query)
            response = await engine.run(request, callbacks=ui.get_callbacks())
            render_final_answer(response)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session interrompue. Au revoir ![/dim]")
            break
        except Exception as exc:
            render_error(format_error_for_display(exc, debug=debug))
        finally:
            ui.stop_spinner()


def main() -> None:
    """Point d'entrée principal synchrone."""
    args = parse_args()
    settings = get_settings()
    setup_logging(settings.log_dir_path, debug=args.debug)
    engine = initialize_engine(settings)
    asyncio.run(run_interactive_repl(engine, debug=args.debug))


if __name__ == "__main__":
    main()
