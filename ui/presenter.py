"""Présentateurs de flux d'événements pour l'affichage d'Ekko.

Découple le moteur de raisonnement ReAct de la couche de rendu.
Fournit ConsolePresenter (Rich interactif) et JsonPresenter (machine-to-machine).
"""

from collections.abc import AsyncIterator
from agent.schemas import (
    AgentEvent,
    AgentResponse,
    DoneEvent,
    PlanEvent,
    RetrievalEvent,
    StreamChunkEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
    ValidationEvent,
)
from rich.live import Live
from rich.markdown import Markdown
from .console import (
    AgentUI,
    console,
    render_final_answer,
    render_thought_line,
    render_thought_panel,
)


class ConsolePresenter:
    """Présentateur adaptant le flux d'événements à la console Rich."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.ui = AgentUI(debug=debug)
        self._has_streamed = False
        self._live: Live | None = None
        self._streamed_text = ""

    def _stop_live(self) -> None:
        """Arrête proprement la vue dynamique Live."""
        if self._live is not None:
            self._live.stop()
            self._live = None

    def render_event(self, event: AgentEvent) -> None:
        """Traite et affiche un événement unitaire du moteur."""
        if isinstance(event, PlanEvent):
            self.ui.on_plan(event.focus, event.queries, event.elapsed)
        elif isinstance(event, RetrievalEvent):
            self.ui.on_retrieval(event.source, event.count, event.elapsed)
        elif isinstance(event, ThoughtEvent):
            self.ui.stop_spinner()
            if self.debug:
                render_thought_panel(event.thought)
            else:
                render_thought_line(event.thought, event.elapsed)
        elif isinstance(event, ToolCallEvent):
            self.ui.on_tool_call(event.tool_name, event.arguments)
        elif isinstance(event, ToolResultEvent):
            self.ui.on_tool_result(event.tool_name, event.result)
        elif isinstance(event, StreamChunkEvent):
            if not self._has_streamed:
                self.ui.stop_spinner()
                self._has_streamed = True
                self._streamed_text = ""
                self._live = Live(
                    Markdown(""),
                    console=console,
                    refresh_per_second=12,
                    vertical_overflow="visible",
                )
                self._live.start()
            self._streamed_text += event.delta
            if self._live is not None:
                self._live.update(Markdown(self._streamed_text))
        elif isinstance(event, ValidationEvent):
            self._stop_live()
            if not self._has_streamed:
                self.ui.on_validation(event.elapsed)
            else:
                console.print(f"[dim magenta]⚡ [3/3] Synthèse certifiée ({event.elapsed:.1f}s)[/dim magenta]")
        elif isinstance(event, DoneEvent):
            self.ui.stop_spinner()
            self._stop_live()
            if not self._has_streamed:
                render_final_answer(event.response)
            else:
                console.print()
                self._has_streamed = False

    async def render_stream(self, stream: AsyncIterator[AgentEvent]) -> AgentResponse | None:
        """Consomme le flux asynchrone d'événements et pilote le rendu en temps réel."""
        final_response: AgentResponse | None = None
        self._has_streamed = False
        self._streamed_text = ""
        self.ui.on_thinking_start()
        try:
            async for event in stream:
                self.render_event(event)
                if isinstance(event, DoneEvent):
                    final_response = event.response
        finally:
            self._stop_live()
            self.ui.stop_spinner()
            self._has_streamed = False
            self._streamed_text = ""
        return final_response


class JsonPresenter:
    """Présentateur silencieux sérialisant la réponse finale en JSON brut."""

    async def render_stream(self, stream: AsyncIterator[AgentEvent]) -> AgentResponse | None:
        """Consomme le flux et imprime l'AgentResponse sous forme de JSON strict."""
        async for event in stream:
            if isinstance(event, DoneEvent):
                print(event.response.model_dump_json(indent=2))
                return event.response
        return None
