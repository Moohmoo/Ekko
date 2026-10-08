"""Tests unitaires pour le moteur de contexte unifié (ExecutionContext)."""

from datetime import datetime
from pathlib import Path
from agent.context import EnvironmentContext, ExecutionContext, build_execution_context
from agent.storage import SessionStorage


def test_environment_context_defaults() -> None:
    """Vérifie que l'environnement capture correctement l'année et la date."""
    now = datetime.now()
    env = EnvironmentContext(
        current_date=now.strftime("%d %B %Y"),
        current_year=now.year,
        current_time=now.strftime("%H:%M"),
        os_name="linux",
        cwd="/workspace",
    )
    assert env.current_year == now.year
    assert env.os_name == "linux"
    assert env.cwd == "/workspace"


def test_build_execution_context_aggregation(tmp_path: Path) -> None:
    """Vérifie la construction instantanée du contexte global avec historique et profil."""
    storage = SessionStorage(tmp_path / "test_ctx.db")
    storage.record_message("s1", "user", "Bonjour")
    storage.record_message("s1", "assistant", "Salut Mohamed")

    ctx = build_execution_context(
        storage=storage,
        session_id="s1",
        user_profile="Profil test Mohamed",
        history_limit=2,
    )

    assert isinstance(ctx, ExecutionContext)
    assert ctx.current_year == datetime.now().year
    assert ctx.user_profile == "Profil test Mohamed"
    assert ctx.session_id == "s1"
    assert len(ctx.messages) == 2
    assert "Bonjour" in ctx.history_block
    assert "Salut Mohamed" in ctx.history_block
