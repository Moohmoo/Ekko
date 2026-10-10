"""Universal ingestion connectors package."""

from ekko.infrastructure.ingestion.connectors.base import BaseConnector
from ekko.infrastructure.ingestion.connectors.rest_api import RestApiConnector
from ekko.infrastructure.ingestion.connectors.rss import RssConnector

__all__ = [
    "BaseConnector",
    "RestApiConnector",
    "RssConnector",
]
