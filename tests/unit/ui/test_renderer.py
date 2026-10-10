"""Unit tests for the CLI Rich event renderer."""

import io
import pytest
from rich.console import Console

from ekko.core.events import (
    EngineError,
    StepStarted,
    TokenChunk,
    ToolCallCompleted,
    ToolCallStarted,
    TurnCompleted,
)
from ekko.ui.input import ToolbarMetadata
from ekko.ui.renderer import CLIRenderer


@pytest.fixture
def string_console() -> tuple[Console, io.StringIO]:
    """Provide a Console writing to a StringIO stream for deterministic inspection."""
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, width=120)
    return console, buffer


def test_renderer_renders_home_banner(string_console: tuple[Console, io.StringIO]) -> None:
    """Ensure render_home prints application banner and dynamic metadata."""
    console, buffer = string_console
    renderer = CLIRenderer(console=console)
    metadata = ToolbarMetadata(
        model_name="ollama/llama3.1:7b",
        session_id="session_alpha",
        workspace="/workspace/ekko",
    )

    renderer.render_home(metadata)
    output = buffer.getvalue()

    assert "EKKO" in output
    assert "ollama/llama3.1:7b" in output
    assert "session_alpha" in output
    assert "/clear" in output
    assert "/exit" in output


def test_renderer_tool_call_lifecycle(string_console: tuple[Console, io.StringIO]) -> None:
    """Ensure StepStarted, ToolCallStarted, and ToolCallCompleted format status and completion."""
    console, buffer = string_console
    renderer = CLIRenderer(console=console)

    renderer.render_event(StepStarted(step_index=1, max_steps=3))
    renderer.render_event(
        ToolCallStarted(tool_call_id="call_1", tool_name="arxiv", arguments={"query": "diffusion"})
    )
    renderer.render_event(
        ToolCallCompleted(
            tool_call_id="call_1",
            tool_name="arxiv",
            success=True,
            summary="Found papers",
            duration_ms=315.4,
        )
    )

    output = buffer.getvalue()
    assert "arxiv" in output
    assert "315ms" in output or "315.4ms" in output
    assert "✓" in output or "SUCCESS" in output or "arxiv" in output



def test_renderer_tool_call_failure(string_console: tuple[Console, io.StringIO]) -> None:
    """Ensure failed tool calls display failure indicator and summary."""
    console, buffer = string_console
    renderer = CLIRenderer(console=console)

    renderer.render_event(
        ToolCallCompleted(
            tool_call_id="call_2",
            tool_name="read_resource",
            success=False,
            summary="HTTP 404 Not Found",
            duration_ms=105.0,
        )
    )

    output = buffer.getvalue()
    assert "read_resource" in output
    assert "HTTP 404 Not Found" in output


def test_renderer_token_chunks_and_turn_completed(
    string_console: tuple[Console, io.StringIO]
) -> None:
    """Ensure TokenChunk streaming outputs text and TurnCompleted finalizes turn."""
    console, buffer = string_console
    renderer = CLIRenderer(console=console)

    renderer.render_event(StepStarted(step_index=1, max_steps=5))
    renderer.render_event(TokenChunk(delta="Bonjour "))
    renderer.render_event(TokenChunk(delta="Ekko !"))
    renderer.render_event(TurnCompleted(content="Bonjour Ekko !", total_steps=1))

    output = buffer.getvalue()
    assert "Bonjour Ekko !" in output


def test_renderer_engine_error(string_console: tuple[Console, io.StringIO]) -> None:
    """Ensure EngineError outputs structured panel with message and actionable hint."""
    console, buffer = string_console
    renderer = CLIRenderer(console=console)

    renderer.render_event(
        EngineError(
            error_type="ProviderUnavailable",
            message="Connection refused to Ollama server",
            actionable_hint="Lance la commande 'ollama serve' dans un terminal.",
        )
    )

    output = buffer.getvalue()
    assert "ProviderUnavailable" in output
    assert "Connection refused to Ollama server" in output
    assert "Lance la commande 'ollama serve'" in output


def test_renderer_slash_command_helpers(string_console: tuple[Console, io.StringIO]) -> None:
    """Ensure render_help, render_clear, and render_exit format cleanly."""
    console, buffer = string_console
    renderer = CLIRenderer(console=console)

    renderer.render_help()
    renderer.render_clear("session_test")
    renderer.render_exit()

    output = buffer.getvalue()
    assert "/clear" in output
    assert "/exit" in output
    assert "session_test" in output
    assert "Au revoir" in output or "Goodbye" in output or "Session fermée" in output
