"""Base abstraction for universal ingestion connectors."""

from abc import ABC, abstractmethod
from ekko.infrastructure.database.models import RawSignal, SourceState
from ekko.infrastructure.ingestion.config import SourceConfig


class BaseConnector(ABC):
    """Abstract connector protocol driving raw signal extraction."""

    @abstractmethod
    async def fetch_signals(
        self,
        source: SourceConfig,
        state: SourceState | None = None,
    ) -> tuple[list[RawSignal], SourceState]:
        """Fetch fresh signals from source using polite polling and update state."""
