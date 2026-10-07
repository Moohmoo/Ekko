"""Tests unitaires pour le point d'entrée cli.py."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from cli import initialize_engine, parse_args, run_interactive_repl
from config import Settings


def test_parse_args_defaults() -> None:
    """Vérifie le parsing des arguments par défaut sans flag debug."""
    with patch("sys.argv", ["ekko"]):
        args = parse_args()
        assert args.debug is False


def test_parse_args_debug_flag() -> None:
    """Vérifie le parsing avec le drapeau -d activé."""
    with patch("sys.argv", ["ekko", "-d"]):
        args = parse_args()
        assert args.debug is True


def test_initialize_engine_creates_instance(tmp_path) -> None:
    """Vérifie que initialize_engine instancie EkkoEngine avec les outils requis."""
    db_file = tmp_path / "test.db"
    settings = Settings(
        db_path=str(db_file),
        memory_dir_path=str(tmp_path),
        log_dir_path=str(tmp_path),
        llm_provider="local",
        local_llm_model="test-model",
    )
    engine = initialize_engine(settings)
    assert engine is not None
    assert engine.provider is not None
    assert engine.registry.get_tool("run_daily_watch") is not None
    assert engine.registry.get_tool("get_system_info") is not None


@pytest.mark.asyncio
async def test_run_interactive_repl_quits() -> None:
    """Vérifie que la boucle REPL se termine immédiatement sur la commande 'exit'."""
    engine = MagicMock()
    with patch("cli.prompt_user_input", return_value="exit"):
        await run_interactive_repl(engine, debug=False)
