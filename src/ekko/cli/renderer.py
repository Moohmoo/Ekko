"""Event-driven terminal renderer powered by Rich."""

from typing import Any
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from ekko.core.events import (
    EngineError,
    EngineEvent,
    StepStarted,
    TokenChunk,
    ToolCallCompleted,
    ToolCallStarted,
    TurnCompleted,
)
from ekko.cli.input import ToolbarMetadata


class CLIRenderer:
    """Renders engine events in terminal with in-place status spinners and markdown."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._status: Any = None
        self._live: Live | None = None
        self._accumulated_text: str = ""
        self._has_tool_run: bool = False

    def _stop_status(self) -> None:
        """Stop running in-place spinner status if active."""
        if self._status is not None:
            self._status.stop()
            self._status = None

    def _start_or_update_status(self, text: str) -> None:
        """Start or update the in-place live spinner status."""
        if self._status is None:
            self._status = self.console.status(text, spinner="dots")
            self._status.start()
        else:
            self._status.update(text)

    def render_home(self, metadata: ToolbarMetadata) -> None:
        """Render clean 2-line header without heavy framing borders."""
        parts = [p for p in (metadata.model_name, metadata.session_id) if p]
        model_part = f"[dim]({' • '.join(parts)})[/dim]" if parts else ""
        self.console.print(f"[bold cyan]EKKO[/] [dim]•[/] [bold]Agentic OS[/] {model_part}")
        self.console.print(
            "[dim]Commands: [cyan]/clear[/] to reset, [cyan]/help[/] for help, [cyan]/exit[/] to quit.[/dim]\n"
        )


    def on_step_started(self, event: StepStarted) -> None:
        """Display in-place reflection status for the current step."""
        if not self._has_tool_run and event.step_index == 1:
            self.console.print()
        self._start_or_update_status(
            f"  [bold blue]Step {event.step_index}/{event.max_steps}[/] • Réflexion..."
        )

    def on_tool_call_started(self, event: ToolCallStarted) -> None:
        """Update in-place spinner to reflect tool execution."""
        self._has_tool_run = True
        self._start_or_update_status(
            f"  [bold blue]Tool[/] • Exécution de [cyan]{event.tool_name}[/]..."
        )

    def on_tool_call_completed(self, event: ToolCallCompleted) -> None:
        """Render indented frozen line with tool result status and latency."""
        self._stop_status()
        self._has_tool_run = True
        duration = f"{event.duration_ms:.0f}ms" if event.duration_ms is not None else ""
        if event.success:
            self.console.print(f"  [bold green]✓[/] [cyan]{event.tool_name}[/] [dim]({duration})[/]")
        else:
            self.console.print(
                f"  [bold red]✗[/] [cyan]{event.tool_name}[/] [dim]({duration})[/] : [yellow]{event.summary}[/]"
            )

    def on_token_chunk(self, event: TokenChunk) -> None:
        """Stream token chunks progressively using in-place Live rendering."""
        self._stop_status()
        self._accumulated_text += event.delta
        if self._live is None:
            self._live = Live(self._accumulated_text, console=self.console, auto_refresh=False)
            self._live.start()
        else:
            self._live.update(self._accumulated_text, refresh=True)

    def on_turn_completed(self, event: TurnCompleted) -> None:
        """Finalize message turn, replace with compiled Markdown, and add breathing room."""
        self._stop_status()
        final_content = event.content or self._accumulated_text
        if self._live is not None:
            self._live.update(Markdown(final_content), refresh=True)
            self._live.stop()
            self._live = None
        elif final_content:
            self.console.print(Markdown(final_content))

        self._accumulated_text = ""
        self._has_tool_run = False
        self.console.print()

    def on_engine_error(self, event: EngineError) -> None:
        """Render formatted error panel highlighting actionable guidance."""
        self._stop_status()
        if self._live is not None:
            self._live.stop()
            self._live = None
        content = f"{event.message}\n\n[bold yellow]Conseil :[/] {event.actionable_hint}"
        self.console.print(
            Panel(
                content,
                title=f"[bold red]Erreur Moteur : {event.error_type}[/]",
                border_style="red",
            )
        )
        self.console.print()

    def render_event(self, event: EngineEvent) -> None:
        """Dispatch received engine event to specific rendering handler."""
        if isinstance(event, StepStarted):
            self.on_step_started(event)
        elif isinstance(event, ToolCallStarted):
            self.on_tool_call_started(event)
        elif isinstance(event, ToolCallCompleted):
            self.on_tool_call_completed(event)
        elif isinstance(event, TokenChunk):
            self.on_token_chunk(event)
        elif isinstance(event, TurnCompleted):
            self.on_turn_completed(event)
        elif isinstance(event, EngineError):
            self.on_engine_error(event)

    def render_help(self) -> None:
        """Render help panel documenting available local control commands."""
        commands = [
            "[bold cyan]/clear[/]   - Efface l'historique de la session courante",
            "[bold cyan]/exit[/]    - Quitte l'application (/quit ou /q)",
            "[bold cyan]/help[/]    - Affiche cette aide (?)",
        ]
        self.console.print(
            Panel("\n".join(commands), title="[bold yellow]Commandes Disponibles[/]", border_style="yellow")
        )

    def render_clear(self, session_id: str) -> None:
        """Render session clearance confirmation."""
        self.console.print(f"[yellow]Session '{session_id}' effacée.[/]")

    def render_exit(self) -> None:
        """Render exit notice on session termination."""
        self.console.print("[dim]Au revoir ! Session fermée.[/dim]")
