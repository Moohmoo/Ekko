"""Composants d'affichage et interface console Rich pour Ekko (Style agy).

Affiche les bannières, le bloc Thought de réflexion, les cartes d'outils
et le rendu Markdown fluide.
"""

from typing import Any
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_banner(model_name: str, provider: str) -> None:
    """Affiche la bannière d'accueil sobre et moderne d'Ekko."""
    header = Text()
    header.append("⚡ Ekko", style="bold cyan")
    header.append(" | Assistant Personnel Local", style="bold white")
    header.append(f" ({provider}: {model_name})\n", style="dim cyan")
    header.append("Tapez votre commande ou 'exit' pour quitter.", style="dim")
    console.print(Panel(header, border_style="cyan", padding=(0, 2)))


def render_thought(thought: str) -> None:
    """Affiche le bloc de raisonnement Thought stylisé comme dans Antigravity."""
    clean_thought = thought.strip()
    if clean_thought:
        console.print(
            Panel(
                Text(clean_thought, style="italic dim white"),
                title="[bold magenta]🧠 Thought[/bold magenta]",
                border_style="magenta",
                padding=(0, 1),
            )
        )


def render_tool_call(tool_name: str, arguments: dict[str, Any]) -> None:
    """Affiche l'appel d'outil avant son exécution."""
    args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
    console.print(
        Panel(
            Text(f"Paramètres : {args_str or 'aucun'}", style="yellow"),
            title=f"[bold yellow]⚙️ Tool Call: {tool_name}[/bold yellow]",
            border_style="yellow",
            padding=(0, 1),
        )
    )


def render_tool_result(tool_name: str, result: str) -> None:
    """Affiche le compte-rendu d'observation retourné par l'outil."""
    console.print(
        Panel(
            Text(result.strip(), style="green"),
            title=f"[bold green]✓ Result: {tool_name}[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
    )


def render_final_answer(answer: str) -> None:
    """Affiche la réponse finale formatée en Markdown."""
    console.print()
    console.print(Markdown(answer.strip()))
    console.print()


def render_error(message: str) -> None:
    """Affiche un message d'erreur clair."""
    console.print(Panel(Text(message, style="bold red"), border_style="red"))
