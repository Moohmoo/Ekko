"""Unit tests for sources.yaml configuration loader and Pydantic schemas."""

from pathlib import Path
import yaml

from ekko.domains.system.loader import load_sources_config
from ekko.domains.system.contracts import SourceConfig, SourcesCatalogConfig


def test_source_config_validation() -> None:
    """Ensure SourceConfig validates supported types and default intervals."""
    cfg = SourceConfig(
        id="test_rss",
        type="rss",
        url="https://example.com/rss.xml",
    )
    assert cfg.id == "test_rss"
    assert cfg.type == "rss"
    assert cfg.interval == "30m"
    assert cfg.max_items == 20


def test_sources_catalog_config_parsing() -> None:
    """Ensure SourcesCatalogConfig deserializes full YAML structure."""
    raw = {
        "sources": [
            {
                "id": "hn_tech",
                "type": "rest_api",
                "url": "https://hn.algolia.com/api/v1/search",
                "interval": "15m",
                "max_items": 25,
                "json_items_path": "hits",
            },
            {
                "id": "ai_feed",
                "type": "rss",
                "url": "https://example.com/feed.xml",
                "interval": "1h",
            },
        ]
    }
    catalog = SourcesCatalogConfig.model_validate(raw)
    assert len(catalog.sources) == 2
    assert catalog.sources[0].id == "hn_tech"
    assert catalog.sources[0].json_items_path == "hits"
    assert catalog.sources[1].id == "ai_feed"


def test_load_sources_config_from_file(tmp_path: Path) -> None:
    """Ensure load_sources_config loads valid sources.yaml correctly."""
    sources_file = tmp_path / "sources.yaml"
    content = {
        "sources": [
            {
                "id": "custom_api",
                "type": "rest_api",
                "url": "https://api.test/feed",
            }
        ]
    }
    sources_file.write_text(yaml.dump(content), encoding="utf-8")

    loaded = load_sources_config(tmp_path)
    assert len(loaded.sources) == 1
    assert loaded.sources[0].id == "custom_api"


def test_load_sources_config_generates_template_if_missing(tmp_path: Path) -> None:
    """Ensure load_sources_config creates sources.yaml.example when missing."""
    catalog = load_sources_config(tmp_path)
    example_path = tmp_path / "sources.yaml.example"
    assert example_path.exists()
    assert len(catalog.sources) == 0
