"""Asynchronous ingestion coordinator and background polling scheduler."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from typing import Any

from ekko.config.loader import load_sources_config
from ekko.config.schemas import SourceConfig, SourcesCatalogConfig
from ekko.ingestion.connectors.base import BaseConnector
from ekko.ingestion.connectors.rest_api import RestApiConnector
from ekko.ingestion.connectors.rss import RssConnector
from ekko.memory.hybrid_store import DatabaseManager
from ekko.memory.models import RawSignal, SourceState
from ekko.utils.logger import get_logger

logger = get_logger("daemon.scheduler")

DURATION_UNITS: dict[str, float] = {
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
}


def parse_interval_seconds(interval_str: str) -> float:
    """Parse string duration (e.g. '30s', '15m', '2h', '1d') into seconds."""
    match = re.match(r"^(\d+)([smhd])$", interval_str.strip().lower())
    if not match:
        return 1800.0
    val, unit = match.groups()
    return float(val) * DURATION_UNITS.get(unit, 1.0)


def _calculate_backoff_delay(consecutive_errors: int) -> float:
    """Calculate exponential backoff seconds for consecutive source polling errors."""
    return min(86400.0, 60.0 * (2 ** min(consecutive_errors, 8)))


class IngestionCoordinator:
    """Coordinates background polite polling of declarative ingestion sources."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        catalog: SourcesCatalogConfig | None = None,
        rss_connector: BaseConnector | None = None,
        rest_connector: BaseConnector | None = None,
        config_dir: Path | str = "config",
    ) -> None:
        self.db_manager = db_manager
        self.catalog = catalog or load_sources_config(config_dir)
        self.rss_connector = rss_connector or RssConnector()
        self.rest_connector = rest_connector or RestApiConnector()
        self._running = False
        self._loop_task: asyncio.Task[None] | None = None

    def _get_connector(self, source_type: str) -> BaseConnector | None:
        """Map source type string to instantiated connector."""
        if source_type == "rss":
            return self.rss_connector
        if source_type == "rest_api":
            return self.rest_connector
        return None

    def _should_poll(self, source: SourceConfig, state: SourceState | None, now: datetime) -> bool:
        """Evaluate whether a source is due for polling based on intervals and backoff."""
        if state is None or state.last_polled_at is None:
            return True
        if state.backoff_until and now < state.backoff_until:
            return False
        interval = parse_interval_seconds(source.interval)
        return (now - state.last_polled_at).total_seconds() >= interval

    async def _handle_polling_error(
        self,
        source: SourceConfig,
        state: SourceState | None,
        now: datetime,
        exc: Exception,
    ) -> None:
        """Record polling error, calculate backoff delay, and persist state update."""
        errors = (state.consecutive_errors if state else 0) + 1
        delay_sec = _calculate_backoff_delay(errors)
        error_state = state or SourceState(
            id=source.id,
            source_type=source.type,
            url_or_path=source.url or "",
        )
        error_state.consecutive_errors = errors
        error_state.backoff_until = now + timedelta(seconds=delay_sec)
        error_state.last_polled_at = now
        await self.db_manager.upsert_source_state(error_state)
        logger.warning("Polling error on source '%s' (%s). Backoff for %ds.", source.id, exc, delay_sec)

    async def poll_source(self, source: SourceConfig) -> list[RawSignal]:
        """Poll a single source if due, persisting signals and updating tracking state."""
        state = await self.db_manager.get_source_state(source.id)
        now = datetime.now(timezone.utc)
        if not self._should_poll(source, state, now):
            return []

        connector = self._get_connector(source.type)
        if not connector:
            return []

        try:
            signals, updated_state = await connector.fetch_signals(source, state=state)
            await self.db_manager.upsert_source_state(updated_state)
            if signals:
                await self.db_manager.save_raw_signals(signals)
            return signals
        except Exception as exc:
            await self._handle_polling_error(source, state, now, exc)
            return []

    async def run_once(self) -> dict[str, int]:
        """Execute a single evaluation pass across all catalog sources."""
        results: dict[str, int] = {}
        for source in self.catalog.sources:
            signals = await self.poll_source(source)
            results[source.id] = len(signals)
        return results

    async def _run_loop(self, poll_interval_seconds: float) -> None:
        """Background continuous scheduler loop."""
        while self._running:
            try:
                await self.run_once()
            except Exception as exc:
                logger.error("Unexpected error in daemon scheduler pass: %s", exc)
            await asyncio.sleep(poll_interval_seconds)

    async def start(self, poll_interval_seconds: float = 60.0) -> None:
        """Start asynchronous background polling scheduler."""
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop(poll_interval_seconds))
        logger.info("Ingestion coordinator scheduler started (interval: %ss).", poll_interval_seconds)

    async def stop(self) -> None:
        """Stop background scheduler cleanly."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        logger.info("Ingestion coordinator scheduler stopped.")
