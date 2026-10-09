"""Unit tests for the REPL CLI driving adapter."""

from unittest.mock import AsyncMock, patch
import pytest

from ekko.core.errors import ProviderError
from ekko.ui.cli import run_repl


@pytest.mark.asyncio
async def test_repl_exits_on_quit_command() -> None:
    """Ensure REPL loop terminates cleanly when user enters quit command."""
    mock_engine = AsyncMock()

    with patch("builtins.input", side_effect=["exit"]):
        await run_repl(mock_engine)

    mock_engine.process_message.assert_not_called()


@pytest.mark.asyncio
async def test_repl_processes_message_then_exits(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure REPL displays engine responses before user quits."""
    mock_engine = AsyncMock()
    mock_engine.process_message.return_value = "Hello from Ekko!"

    with patch("builtins.input", side_effect=["Hi there", "quit"]):
        await run_repl(mock_engine)

    mock_engine.process_message.assert_awaited_once_with("Hi there", session_id="default")
    captured = capsys.readouterr().out
    assert "Ekko: Hello from Ekko!" in captured


@pytest.mark.asyncio
async def test_repl_handles_provider_error_gracefully(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure REPL prints error message without crashing when provider fails."""
    mock_engine = AsyncMock()
    mock_engine.process_message.side_effect = [
        ProviderError("Network unreachable"),
        "Recovered reply",
    ]

    with patch("builtins.input", side_effect=["Ping 1", "Ping 2", "exit"]):
        await run_repl(mock_engine)

    captured = capsys.readouterr().out
    assert "Error: Network unreachable" in captured
    assert "Ekko: Recovered reply" in captured


@pytest.mark.asyncio
async def test_repl_handles_keyboard_interrupt(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure Ctrl+C exits gracefully without uncaught traceback."""
    mock_engine = AsyncMock()

    with patch("builtins.input", side_effect=KeyboardInterrupt):
        await run_repl(mock_engine)

    captured = capsys.readouterr().out
    assert "Session closed." in captured
