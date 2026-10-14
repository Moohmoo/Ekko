"""Unit tests for IngestionCoordinator / DaemonScheduler."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from ekko.core.models import RawSignal, SignalStatus, SourceState
from ekko.daemon.scheduler import IngestionCoordinator, parse_interval_seconds
from ekko.domains.system.schemas import SourceConfig, SourcesCatalogConfig


def test_parse_interval_seconds() -> None:
    """Ensure string duration specs are converted to seconds accurately."""
    assert parse_interval_seconds("30s") == 30.0
    assert parse_interval_seconds("15m") == 900.0
    assert parse_interval_seconds("1h") == 3600.0
    assert parse_interval_seconds("2h") == 7200.0
    assert parse_interval_seconds("1d") == 86400.0
    assert parse_interval_seconds("invalid") == 1800.0


@pytest.mark.asyncio
async def test_scheduler_polls_due_source_and_persists_signals() -> None:
    """Ensure scheduler triggers connector for due sources and saves raw signals."""
    mock_db = MagicMock()
    mock_db.get_source_state = AsyncMock(return_value=None)
    mock_db.save_raw_signals = AsyncMock(return_value=2)
    mock_db.upsert_source_state = AsyncMock()

    mock_rss_connector = MagicMock()
    sample_signals = [
        RawSignal(id="s1", source_id="src1", title="Title 1", status=SignalStatus.PENDING),
        RawSignal(id="s2", source_id="src1", title="Title 2", status=SignalStatus.PENDING),
    ]
    updated_state = SourceState(id="src1", source_type="rss", url_or_path="https://feed.xml")
    mock_rss_connector.fetch_signals = AsyncMock(return_value=(sample_signals, updated_state))

    source = SourceConfig(id="src1", type="rss", url="https://feed.xml", interval="15m")
    catalog = SourcesCatalogConfig(sources=[source])

    coordinator = IngestionCoordinator(
        db_manager=mock_db,
        catalog=catalog,
        rss_connector=mock_rss_connector,
    )

    results = await coordinator.run_once()

    assert results["src1"] == 2
    mock_rss_connector.fetch_signals.assert_awaited_once()
    mock_db.save_raw_signals.assert_awaited_once_with(sample_signals)
    mock_db.upsert_source_state.assert_awaited_once_with(updated_state)


@pytest.mark.asyncio
async def test_scheduler_skips_source_if_interval_not_elapsed() -> None:
    """Ensure scheduler does not poll if last_polled_at is within interval."""
    mock_db = MagicMock()
    now = datetime.now(timezone.utc)
    recent_state = SourceState(
        id="src_fresh",
        source_type="rss",
        url_or_path="https://fresh.xml",
        last_polled_at=now - timedelta(minutes=5),  # polled 5 mins ago, interval is 30m
    )
    mock_db.get_source_state = AsyncMock(return_value=recent_state)

    mock_rss = MagicMock()
    mock_rss.fetch_signals = AsyncMock()

    source = SourceConfig(id="src_fresh", type="rss", url="https://fresh.xml", interval="30m")
    coordinator = IngestionCoordinator(
        db_manager=mock_db,
        catalog=SourcesCatalogConfig(sources=[source]),
        rss_connector=mock_rss,
    )

    results = await coordinator.run_once()

    assert results["src_fresh"] == 0
    mock_rss.fetch_signals.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_handles_network_failure_defensively() -> None:
    """Ensure transient network errors do not crash daemon and increment consecutive_errors."""
    mock_db = MagicMock()
    mock_db.get_source_state = AsyncMock(return_value=None)
    mock_db.upsert_source_state = AsyncMock()

    mock_rest = MagicMock()
    mock_rest.fetch_signals = AsyncMock(side_effect=Exception("Network unreachable"))

    source = SourceConfig(id="api_fail", type="rest_api", url="https://fail.api", interval="10m")
    coordinator = IngestionCoordinator(
        db_manager=mock_db,
        catalog=SourcesCatalogConfig(sources=[source]),
        rest_connector=mock_rest,
    )

    results = await coordinator.run_once()

    assert results["api_fail"] == 0
    mock_db.upsert_source_state.assert_awaited_once()
    saved_state: SourceState = mock_db.upsert_source_state.call_args[0][0]
    assert saved_state.consecutive_errors == 1
    assert saved_state.backoff_until is not None


@pytest.mark.asyncio
async def test_scheduler_triggers_distiller_after_polling() -> None:
    """Ensure run_once calls distill_batch when a distiller is provided."""
    mock_db = MagicMock()
    mock_distiller = MagicMock()
    mock_distiller.distill_batch = AsyncMock(return_value=3)

    coordinator = IngestionCoordinator(
        db_manager=mock_db,
        catalog=SourcesCatalogConfig(sources=[]),
        distiller=mock_distiller,
        auto_distill=True,
    )

    results = await coordinator.run_once()

    assert results["distilled"] == 3
    mock_distiller.distill_batch.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduler_skips_distiller_when_auto_distill_is_false() -> None:
    """Ensure run_once does not trigger distiller when auto_distill is False."""
    mock_db = MagicMock()
    mock_distiller = MagicMock()
    mock_distiller.distill_batch = AsyncMock(return_value=3)

    coordinator = IngestionCoordinator(
        db_manager=mock_db,
        catalog=SourcesCatalogConfig(sources=[]),
        distiller=mock_distiller,
        auto_distill=False,
    )

    results = await coordinator.run_once()

    assert "distilled" not in results
    mock_distiller.distill_batch.assert_not_called()



@pytest.mark.asyncio
async def test_coordinator_anti_overlap_skips_when_locked() -> None:
    """Ensure run_once skips execution and returns empty dict when another cycle holds the lock."""
    mock_db = MagicMock()
    coordinator = IngestionCoordinator(
        db_manager=mock_db,
        catalog=SourcesCatalogConfig(sources=[]),
    )

    # Simulate locked coordinator (in-flight run_once)
    await coordinator._lock.acquire()
    try:
        results = await coordinator.run_once()
        assert results == {}
    finally:
        coordinator._lock.release()


