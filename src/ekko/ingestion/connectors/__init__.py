"""Ingestion connectors package exposing base and specialized implementations."""

from ekko.ingestion.connectors.base import BaseConnector
from ekko.ingestion.connectors.rest_api import RestApiConnector
from ekko.ingestion.connectors.rss import RssConnector

__all__ = ["BaseConnector", "RestApiConnector", "RssConnector"]
