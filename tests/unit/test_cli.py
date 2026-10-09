"""Unit tests for the REPL CLI driving adapter."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ekko.core.errors import ProviderError
from ekko.ui.cli import main, parse_args, run_repl


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


def test_parse_args_defaults() -> None:
    """Ensure parse_args defaults to session 'default' and clear=False."""
    args = parse_args([])
    assert args.session == "default"
    assert args.clear is False


def test_parse_args_custom_session() -> None:
    """Ensure parse_args accepts custom session argument."""
    args = parse_args(["--session", "work_project"])
    assert args.session == "work_project"
    assert args.clear is False

    short_args = parse_args(["-s", "short_sess"])
    assert short_args.session == "short_sess"


def test_parse_args_clear_flag() -> None:
    """Ensure parse_args detects --clear flag."""
    args = parse_args(["--clear"])
    assert args.session == "default"
    assert args.clear is True


@patch("ekko.ui.cli.SqliteMemory")
@patch("ekko.ui.cli.EkkoEngine")
@patch("ekko.ui.cli.run_repl")
def test_main_wires_sqlite_and_runs_repl(
    mock_run_repl: MagicMock,
    mock_engine_cls: MagicMock,
    mock_sqlite_cls: MagicMock,
) -> None:
    """Ensure main initializes SqliteMemory and passes target session to REPL."""
    mock_sqlite_instance = MagicMock()
    mock_sqlite_cls.return_value = mock_sqlite_instance
    mock_run_repl.return_value = None

    with patch("sys.argv", ["ekko", "--session", "custom_sess"]):
        main()

    mock_sqlite_cls.assert_called_once()
    mock_engine_cls.assert_called_once()
    _, kwargs = mock_engine_cls.call_args
    assert kwargs["memory"] == mock_sqlite_instance


@patch("ekko.ui.cli.SqliteMemory")
@patch("ekko.ui.cli.EkkoEngine")
@patch("ekko.ui.cli.run_repl")
def test_main_clears_session_when_flag_present(
    mock_run_repl: MagicMock,
    mock_engine_cls: MagicMock,
    mock_sqlite_cls: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Ensure main clears the session before starting REPL when --clear is provided."""
    mock_sqlite_instance = MagicMock()
    mock_sqlite_instance.clear_session = AsyncMock()
    mock_sqlite_cls.return_value = mock_sqlite_instance
    mock_run_repl.return_value = None

    with patch("sys.argv", ["ekko", "--session", "temp_sess", "--clear"]):
        main()

    mock_sqlite_instance.clear_session.assert_awaited_once_with("temp_sess")
    captured = capsys.readouterr().out
    assert "Session 'temp_sess' cleared." in captured
