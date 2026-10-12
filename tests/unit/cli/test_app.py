"""Unit tests for the modern CLI application loop."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ekko.core.events import StepStarted, TokenChunk, TurnCompleted
from ekko.settings import Settings
from ekko.cli.app import main, run_app
from ekko.cli.input import CommandType, ToolbarMetadata, UserInput



@pytest.mark.asyncio
async def test_run_app_exits_on_exit_command() -> None:
    """Ensure run_app terminates and renders exit notice on EXIT command."""
    mock_engine = AsyncMock()
    mock_memory = AsyncMock()
    mock_input = AsyncMock()
    mock_input.get_input.side_effect = [UserInput(command=CommandType.EXIT)]
    mock_renderer = MagicMock()

    await run_app(
        engine=mock_engine,
        memory=mock_memory,
        input_handler=mock_input,
        renderer=mock_renderer,
        metadata=ToolbarMetadata(model_name="mock-model", session_id="s1"),
    )

    mock_renderer.render_home.assert_called_once()
    mock_renderer.render_exit.assert_called_once()
    mock_engine.run_stream.assert_not_called()


@pytest.mark.asyncio
async def test_run_app_clears_session_on_clear_command() -> None:
    """Ensure run_app clears session in memory and notifies renderer."""
    mock_engine = AsyncMock()
    mock_memory = AsyncMock()
    mock_input = AsyncMock()
    mock_input.get_input.side_effect = [
        UserInput(command=CommandType.CLEAR, text="/clear"),
        UserInput(command=CommandType.EXIT),
    ]
    mock_renderer = MagicMock()

    await run_app(
        engine=mock_engine,
        memory=mock_memory,
        input_handler=mock_input,
        renderer=mock_renderer,
        session_id="custom_sess",
    )

    mock_memory.clear_session.assert_awaited_once_with("custom_sess")
    mock_renderer.render_clear.assert_called_once_with("custom_sess")


@pytest.mark.asyncio
async def test_run_app_shows_help_on_help_command() -> None:
    """Ensure run_app renders help panel on HELP command."""
    mock_engine = AsyncMock()
    mock_memory = AsyncMock()
    mock_input = AsyncMock()
    mock_input.get_input.side_effect = [
        UserInput(command=CommandType.HELP, text="/help"),
        UserInput(command=CommandType.EXIT),
    ]
    mock_renderer = MagicMock()

    await run_app(
        engine=mock_engine,
        memory=mock_memory,
        input_handler=mock_input,
        renderer=mock_renderer,
    )

    mock_renderer.render_help.assert_called_once()


@pytest.mark.asyncio
async def test_run_app_streams_engine_events() -> None:
    """Ensure run_app dispatches every engine stream event to renderer."""
    mock_engine = MagicMock()

    async def fake_stream(user_input: str, session_id: str):
        yield StepStarted(step_index=1, max_steps=1)
        yield TokenChunk(delta="Hello ")
        yield TurnCompleted(content="Hello ", total_steps=1)

    mock_engine.run_stream = fake_stream
    mock_memory = AsyncMock()
    mock_input = AsyncMock()
    mock_input.get_input.side_effect = [
        UserInput(command=CommandType.USER_PROMPT, text="Say hello"),
        UserInput(command=CommandType.EXIT),
    ]
    mock_renderer = MagicMock()

    await run_app(
        engine=mock_engine,
        memory=mock_memory,
        input_handler=mock_input,
        renderer=mock_renderer,
        session_id="s_stream",
    )

    assert mock_renderer.render_event.call_count == 3


@pytest.mark.asyncio
async def test_run_app_handles_keyboard_interrupt_during_stream() -> None:
    """Ensure Ctrl+C during streaming cancels turn gracefully without crashing."""
    mock_engine = MagicMock()

    async def interrupted_stream(user_input: str, session_id: str):
        yield StepStarted(step_index=1, max_steps=1)
        raise KeyboardInterrupt()

    mock_engine.run_stream = interrupted_stream
    mock_memory = AsyncMock()
    mock_input = AsyncMock()
    mock_input.get_input.side_effect = [
        UserInput(command=CommandType.USER_PROMPT, text="Hang"),
        UserInput(command=CommandType.EXIT),
    ]
    mock_renderer = MagicMock()

    await run_app(
        engine=mock_engine,
        memory=mock_memory,
        input_handler=mock_input,
        renderer=mock_renderer,
    )

    assert mock_renderer.render_event.call_count == 1
    mock_renderer.render_exit.assert_called_once()


def test_main_initialization_with_real_settings() -> None:
    """Ensure main initializes without AttributeError using real Settings instance."""
    real_settings = Settings()

    with patch("sys.argv", ["ekko", "--session", "real_test", "--clear"]):
        with patch("ekko.cli.app.Settings", return_value=real_settings):
            with patch("ekko.cli.app.setup_logger"):
                with patch("ekko.cli.app.load_core_prompt"):
                    with patch("ekko.cli.app.load_user_context"):
                        with patch("ekko.cli.app.load_plugins_config"):
                            with patch("ekko.cli.app.build_system_prompt", return_value="System prompt"):
                                with patch("ekko.cli.app.ToolCatalog"):
                                    with patch("ekko.cli.app.LLMRouter"):
                                        with patch("ekko.cli.app.SqliteMemory"):
                                            with patch("ekko.cli.app.HybridStore"):
                                                with patch("ekko.cli.app.run_app", new_callable=AsyncMock) as mock_run_app:
                                                    main()

                                                mock_run_app.assert_awaited_once()
                                                _, kwargs = mock_run_app.call_args
                                                assert kwargs["session_id"] == "real_test"
                                                assert kwargs["clear"] is True
                                                assert kwargs["metadata"].session_id == "real_test"
                                                assert kwargs["metadata"].model_name != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("exit_word", ["exit", "quit", "q", ":q", " EXIT ", "Quit"])
async def test_run_app_exits_on_textual_exit_commands(exit_word: str) -> None:
    """Ensure run_app treats textual exit/quit words as exit commands without invoking engine."""
    mock_engine = AsyncMock()
    mock_memory = AsyncMock()
    mock_input = AsyncMock()
    mock_input.get_input.side_effect = [UserInput(command=CommandType.USER_PROMPT, text=exit_word)]
    mock_renderer = MagicMock()

    await run_app(
        engine=mock_engine,
        memory=mock_memory,
        input_handler=mock_input,
        renderer=mock_renderer,
    )

    mock_renderer.render_exit.assert_called_once()
    mock_engine.run_stream.assert_not_called()


@pytest.mark.asyncio
async def test_run_app_catches_keyboard_interrupt_gracefully() -> None:
    """Ensure KeyboardInterrupt in input loop renders exit cleanly without unhandled exception."""
    mock_engine = AsyncMock()
    mock_memory = AsyncMock()
    mock_input = AsyncMock()
    mock_input.get_input.side_effect = KeyboardInterrupt()
    mock_renderer = MagicMock()

    await run_app(
        engine=mock_engine,
        memory=mock_memory,
        input_handler=mock_input,
        renderer=mock_renderer,
    )

    mock_renderer.render_exit.assert_called_once()
    mock_engine.run_stream.assert_not_called()



