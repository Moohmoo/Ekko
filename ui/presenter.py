"""Présentateurs de flux d'événements pour l'affichage d'Ekko.

Découple le moteur de raisonnement ReAct de la couche de rendu.
Fournit ConsolePresenter (Rich interactif) et JsonPresenter (machine-to-machine).
"""

from collections.abc import AsyncIterator
from agent.schemas import (
    AgentEvent,
    AgentResponse,
    DoneEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from .console import (
    AgentUI,
    render_final_answer,
    render_thought_line,
    render_thought_panel,
)


class ConsolePresenter:
    """Présentateur adaptant le flux d'événements à la console Rich."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.ui = AgentUI(debug=debug)

    def render_event(self, event: AgentEvent) -> None:
        """Traite et affiche un événement unitaire du moteur."""
        if isinstance(event, ThoughtEvent):
            self.ui.stop_spinner()
            if self.debug:
                render_thought_panel(event.thought)
            else:
                render_thought_line(event.thought, event.elapsed)
        elif isinstance(event, ToolCallEvent):
            self.ui.on_tool_call(event.tool_name, event.arguments)
        elif isinstance(event, ToolResultEvent):
            self.ui.on_tool_result(event.tool_name, event.result)
        elif isinstance(event, DoneEvent):
            self.ui.stop_spinner()
            render_final_answer(event.response)

    async def render_stream(self, stream: AsyncIterator[AgentEvent]) -> AgentResponse | None:
        """Consomme le flux asynchrone d'événements et pilote le rendu en temps réel."""
        final_response: AgentResponse | None = None
        self.ui.on_thinking_start()
        try:
            async for event in stream:
                self.render_event(event)
                if isinstance(event, DoneEvent):
                    final_response = event.response
        finally:
            self.ui.stop_spinner()
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
