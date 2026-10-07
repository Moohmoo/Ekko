"""Composants d'interface console Rich pour Ekko (Style Antigravity agy).

Gère les indicateurs discrets de réflexion et d'outils en mode normal,
et les panneaux détaillés en mode debug (-d / --debug).
"""

import time
from typing import Any
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.text import Text

console = Console()


def print_banner(model_name: str, provider: str, debug: bool = False) -> None:
    """Affiche la bannière d'accueil sobre et moderne d'Ekko."""
    header = Text()
    header.append("⚡ Ekko", style="bold cyan")
    header.append(" | Assistant Personnel Local", style="bold white")
    mode_label = " [debug]" if debug else ""
    header.append(f" ({provider}: {model_name}{mode_label})\n", style="dim cyan")
    header.append("Tapez votre message ou 'exit' pour quitter.", style="dim")
    console.print(Panel(header, border_style="cyan", padding=(0, 2)))


def render_thought_line(thought: str, elapsed: float) -> None:
    """Affiche un indicateur de pensée discret à la agy."""
    single_line = " ".join(thought.strip().split())
    snippet = single_line[:70] + "..." if len(single_line) > 70 else single_line
    console.print(f"[dim]○ Thought for {elapsed:.1f}s ({snippet})[/dim]")


def render_thought_panel(thought: str) -> None:
    """Affiche le panneau verbeux de Thought en mode debug."""
    console.print(
        Panel(
            Text(thought.strip(), style="italic dim white"),
            title="[bold magenta]🧠 Thought (Debug)[/bold magenta]",
            border_style="magenta",
            padding=(0, 1),
        )
    )


def render_tool_call_panel(tool_name: str, arguments: dict[str, Any]) -> None:
    """Affiche l'appel d'outil détaillé en mode debug."""
    args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
    console.print(
        Panel(
            Text(f"Arguments : {args_str or 'aucun'}", style="yellow"),
            title=f"[bold yellow]⚙️ Tool Call: {tool_name}[/bold yellow]",
            border_style="yellow",
            padding=(0, 1),
        )
    )


def render_tool_result_panel(tool_name: str, result: str) -> None:
    """Affiche l'observation brute de l'outil en mode debug."""
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
    """Affiche un message d'erreur d'exécution."""
    console.print(Panel(Text(message, style="bold red"), border_style="red"))


class AgentUI:
    """Coordinateur visuel de l'agent gérant les transitions et spinners."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self._status: Status | None = None
        self._step_start: float = 0.0

    def on_thinking_start(self) -> None:
        """Démarre le spinner d'attente pour la réflexion du modèle."""
        self._step_start = time.perf_counter()
        self._status = console.status("[dim]Réflexion en cours...[/dim]", spinner="dots")
        self._status.start()

    def on_thought(self, thought: str) -> None:
        """Arrête le spinner et affiche la pensée (discrète ou détaillée)."""
        self.stop_spinner()
        elapsed = max(0.1, time.perf_counter() - self._step_start)
        if self.debug:
            render_thought_panel(thought)
        else:
            render_thought_line(thought, elapsed)

    def on_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Démarre l'exécution d'un outil avec spinner contextuel."""
        self.stop_spinner()
        if self.debug:
            render_tool_call_panel(tool_name, arguments)
        self._status = console.status(f"[dim]Exécution de {tool_name}...[/dim]", spinner="dots")
        self._status.start()

    def on_tool_result(self, tool_name: str, result: str) -> None:
        """Termine l'exécution d'un outil."""
        self.stop_spinner()
        if self.debug:
            render_tool_result_panel(tool_name, result)
        else:
            console.print(f"[dim]● Ran tool {tool_name}[/dim]")

    def stop_spinner(self) -> None:
        """Arrête proprement le spinner en cours s'il existe."""
        if self._status is not None:
            self._status.stop()
            self._status = None

    def get_callbacks(self) -> dict[str, Any]:
        """Retourne le mapping de callbacks pour le moteur ReAct."""
        return {
            "on_thinking_start": self.on_thinking_start,
            "on_thought": self.on_thought,
            "on_tool_call": self.on_tool_call,
            "on_tool_result": self.on_tool_result,
        }
