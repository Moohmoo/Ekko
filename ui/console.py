"""Composants d'interface console Rich pour Ekko (Style Antigravity agy).

Gère les indicateurs discrets de réflexion et d'outils en mode normal,
et les panneaux détaillés en mode debug (-d / --debug).
"""

import asyncio
import time
from typing import Any
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

from agent.schemas import AgentResponse

console = Console()

ASCII_LOGO = (
    "[bold cyan]   ▄▄██▄▄   [/bold cyan]",
    "[bold cyan]  ▄█ ▄▄ █▄  [/bold cyan]",
    "[cyan] ██ ▀▀▀▀ ██ [/cyan]",
    "[dim cyan]  ▀█ ▄▄ █▀  [/dim cyan]",
    "[dim cyan]   ▀▀██▀▀   [/dim cyan]",
)


def print_banner(model_name: str, provider: str, debug: bool = False) -> None:
    """Affiche la bannière d'accueil moderne et le logo ASCII d'Ekko."""
    mode_label = " [bold magenta][debug][/bold magenta]" if debug else ""
    info_lines = [
        "[bold white]Ekko CLI[/bold white] [dim cyan]0.1.0[/dim cyan]",
        f"[cyan]{provider}: {model_name}[/cyan]{mode_label}",
        "[dim]~[/dim]",
        "[dim]Tapez votre message, '/reset' ou 'exit' pour quitter.[/dim]",
        "",
    ]
    grid = Table.grid(padding=(0, 3))
    for logo_part, info_part in zip(ASCII_LOGO, info_lines):
        grid.add_row(logo_part, info_part)

    console.print()
    console.print(grid)
    console.print()


def prompt_user_input() -> str:
    """Affiche le délimiteur supérieur et invite l'utilisateur à saisir sa requête."""
    console.print("[dim cyan]" + "─" * 60 + "[/dim cyan]")
    try:
        query = console.input("[bold cyan]> [/bold cyan]").strip()
    except (KeyboardInterrupt, EOFError):
        console.print()
        return "exit"
    if query:
        console.print("[dim cyan]" + "─" * 60 + "[/dim cyan]")
    return query


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


def format_markdown_output(text: str) -> str:
    """Aère et normalise la syntaxe Markdown (titres, puces) avant restitution."""
    import re

    cleaned = text.strip()
    cleaned = re.sub(r"(?<!\n)\s*###\s+", "\n\n### ", cleaned)
    cleaned = re.sub(r"(?<=[^\n])\s+-\s+(?=\*?[A-Za-z])", "\n- ", cleaned)
    return cleaned


def render_final_answer(answer: AgentResponse | str) -> None:
    """Affiche la réponse finale formatée en Markdown et aérée."""
    raw_content = answer.content if isinstance(answer, AgentResponse) else answer
    formatted_content = format_markdown_output(raw_content)
    console.print()
    console.print(Markdown(formatted_content))
    console.print()


def render_error(message: str) -> None:
    """Affiche un message d'erreur d'exécution mis en forme."""
    content = Text.from_markup(message) if "[" in message else Text(message, style="bold red")
    console.print(Panel(content, border_style="red"))


class AgentUI:
    """Coordinateur visuel de l'agent gérant les transitions et spinners."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self._status: Status | None = None
        self._timer_task: asyncio.Task[None] | None = None
        self._step_start: float = 0.0

    def _start_spinner(self, label: str) -> None:
        """Démarre le spinner et lance la mise à jour dynamique du chronomètre."""
        self.stop_spinner()
        self._step_start = time.perf_counter()
        self._status = console.status(f"[dim]{label} (0.0s)[/dim]", spinner="dots")
        self._status.start()
        try:
            loop = asyncio.get_running_loop()
            self._timer_task = loop.create_task(self._update_timer(label))
        except RuntimeError:
            self._timer_task = None

    async def _update_timer(self, label: str) -> None:
        """Met à jour le chronomètre affiché dans le spinner toutes les 300ms."""
        try:
            while self._status is not None:
                await asyncio.sleep(0.3)
                if self._status is not None:
                    elapsed = time.perf_counter() - self._step_start
                    self._status.update(f"[dim]{label} ({elapsed:.1f}s)[/dim]")
        except asyncio.CancelledError:
            pass

    def on_thinking_start(self) -> None:
        """Démarre le spinner dynamique pour la réflexion du modèle."""
        self._start_spinner("Cadrage et analyse de la demande...")

    def on_plan(self, focus: str, queries: list[str], elapsed: float) -> None:
        """Affiche le cadrage de la recherche et relance le spinner de collecte."""
        self.stop_spinner()
        queries_str = ", ".join(f"'{q}'" for q in queries) if queries else "direct"
        console.print(f"[dim cyan]🔍 [1/3] Cadrage : {focus} ({elapsed:.1f}s)[/dim cyan]")
        if self.debug and queries:
            console.print(f"[dim]   Requêtes : {queries_str}[/dim]")
        if queries:
            self._start_spinner(f"Collecte des sources ({focus})...")

    def on_retrieval(self, source: str, count: int, elapsed: float) -> None:
        """Affiche la collecte et démarre le spinner de synthèse."""
        self.stop_spinner()
        console.print(f"[dim green]📚 [2/3] Collecte : {count} sources vérifiées ({elapsed:.1f}s)[/dim green]")
        self._start_spinner("Rédaction de la synthèse technique...")

    def on_validation(self, elapsed: float) -> None:
        """Affiche la certification de validation."""
        self.stop_spinner()
        console.print(f"[dim magenta]⚡ [3/3] Synthèse certifiée ({elapsed:.1f}s)[/dim magenta]")

    def on_thought(self, thought: str) -> None:
        """Arrête le spinner et affiche la pensée (discrète ou détaillée)."""
        self.stop_spinner()
        elapsed = max(0.1, time.perf_counter() - self._step_start)
        if self.debug:
            render_thought_panel(thought)
        else:
            render_thought_line(thought, elapsed)

    def on_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Démarre l'exécution d'un outil avec spinner dynamique."""
        self.stop_spinner()
        if self.debug:
            render_tool_call_panel(tool_name, arguments)
        self._start_spinner(f"Exécution de {tool_name}...")

    def on_tool_result(self, tool_name: str, result: str) -> None:
        """Termine l'exécution d'un outil."""
        self.stop_spinner()
        if self.debug:
            render_tool_result_panel(tool_name, result)
        else:
            console.print(f"[dim]● Ran tool {tool_name}[/dim]")

    def stop_spinner(self) -> None:
        """Arrête proprement le spinner et annule la tâche de mise à jour."""
        if self._timer_task is not None:
            self._timer_task.cancel()
            self._timer_task = None
        if self._status is not None:
            self._status.stop()
            self._status = None
