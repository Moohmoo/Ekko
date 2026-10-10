"""Unit tests for the CLI input handler and slash commands."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from ekko.cli.input import (
    CLIInputHandler,
    CommandType,
    ToolbarMetadata,
    UserInput,
    format_bottom_toolbar,
    parse_slash_command,
)


def test_parse_slash_command_exit() -> None:
    """Ensure exit slash commands are detected."""
    assert parse_slash_command("/exit") == CommandType.EXIT
    assert parse_slash_command("/quit") == CommandType.EXIT
    assert parse_slash_command("/q") == CommandType.EXIT
    assert parse_slash_command("  /exit  ") == CommandType.EXIT


def test_parse_slash_command_clear() -> None:
    """Ensure clear slash command is detected."""
    assert parse_slash_command("/clear") == CommandType.CLEAR
    assert parse_slash_command("  /clear  ") == CommandType.CLEAR


def test_parse_slash_command_help() -> None:
    """Ensure help slash commands are detected."""
    assert parse_slash_command("/help") == CommandType.HELP
    assert parse_slash_command("?") == CommandType.HELP
    assert parse_slash_command("  ?  ") == CommandType.HELP


def test_parse_slash_command_regular_text() -> None:
    """Ensure standard prompts return None for slash command parsing."""
    assert parse_slash_command("Hello Ekko") is None
    assert parse_slash_command("/not_a_command") is None
    assert parse_slash_command("") is None


def test_format_bottom_toolbar_dynamic_metadata() -> None:
    """Ensure bottom toolbar renders injected metadata dynamically without hardcoding."""
    meta = ToolbarMetadata(
        model_name="ollama/qwen2.5:7b",
        session_id="research_session",
        workspace="/home/user/project",
    )
    tokens = format_bottom_toolbar(meta)

    rendered_text = "".join(token[1] for token in tokens)
    assert "ollama/qwen2.5:7b" in rendered_text
    assert "research_session" in rendered_text
    assert "/home/user/project" in rendered_text


@pytest.mark.asyncio
async def test_cli_input_handler_returns_user_prompt() -> None:
    """Ensure standard user input returns USER_PROMPT command."""
    mock_session = AsyncMock()
    mock_session.prompt_async.return_value = "Quelle est la capitale de la France ?"

    handler = CLIInputHandler(session=mock_session)
    result = await handler.get_input()

    assert result == UserInput(
        command=CommandType.USER_PROMPT,
        text="Quelle est la capitale de la France ?",
    )


@pytest.mark.asyncio
async def test_cli_input_handler_intercepts_slash_command() -> None:
    """Ensure slash commands are intercepted without reaching downstream engine."""
    mock_session = AsyncMock()
    mock_session.prompt_async.return_value = " /clear "

    handler = CLIInputHandler(session=mock_session)
    result = await handler.get_input()

    assert result == UserInput(command=CommandType.CLEAR, text="/clear")


@pytest.mark.asyncio
async def test_cli_input_handler_handles_keyboard_interrupt() -> None:
    """Ensure Ctrl+C gracefully returns INTERRUPT command without crashing."""
    mock_session = AsyncMock()
    mock_session.prompt_async.side_effect = KeyboardInterrupt()

    handler = CLIInputHandler(session=mock_session)
    result = await handler.get_input()

    assert result == UserInput(command=CommandType.INTERRUPT, text="")


@pytest.mark.asyncio
async def test_cli_input_handler_handles_eof_error() -> None:
    """Ensure Ctrl+D gracefully returns EXIT command without crashing."""
    mock_session = AsyncMock()
    mock_session.prompt_async.side_effect = EOFError()

    handler = CLIInputHandler(session=mock_session)
    result = await handler.get_input()

    assert result == UserInput(command=CommandType.EXIT, text="")


def test_cli_input_handler_initializes_history_directory(tmp_path: Path) -> None:
    """Ensure history parent directory is created if it does not exist."""
    history_file = tmp_path / "nested" / "dir" / ".ekko_history"
    assert not history_file.parent.exists()

    handler = CLIInputHandler(history_file=history_file)
    assert history_file.parent.exists()
    assert handler.history_file == history_file
