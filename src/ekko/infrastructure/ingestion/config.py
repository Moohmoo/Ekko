"""Pydantic schemas and loader for declarative sources configuration."""

from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field
import yaml

from ekko.utils.logger import get_logger

logger = get_logger("infrastructure.ingestion.config")

EXAMPLE_SOURCES_YAML = """# Ekko V2 Declarative Sources Configuration
sources:
  - id: hn_tech
    type: rest_api
    url: "https://hn.algolia.com/api/v1/search?tags=story&numericFilters=points>150"
    interval: "30m"
    max_items: 20
    json_items_path: "hits"
  - id: arxiv_ai
    type: rss
    url: "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=lastUpdatedDate&max_results=10"
    interval: "2h"
    max_items: 10
"""


class SourceConfig(BaseModel):
    """Configuration model for an individual declarative ingestion source."""

    id: str
    type: Literal["rss", "rest_api", "web_reader", "local_dir"]
    url: str | None = None
    path: str | None = None
    interval: str = "30m"
    max_items: int = 20
    params: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    json_items_path: str | None = None
    field_mapping: dict[str, str] = Field(default_factory=dict)


class SourcesCatalogConfig(BaseModel):
    """Collection catalog of all active ingestion sources."""

    sources: list[SourceConfig] = Field(default_factory=list)


def _ensure_template(example_path: Path) -> None:
    """Write sources.yaml.example template if absent."""
    example_path.parent.mkdir(parents=True, exist_ok=True)
    if not example_path.exists():
        example_path.write_text(EXAMPLE_SOURCES_YAML, encoding="utf-8")
        logger.info("Generated sources template: %s", example_path)


def load_sources_config(config_dir: Path | str) -> SourcesCatalogConfig:
    """Load sources.yaml or create example template with resilient fallback."""
    dir_path = Path(config_dir)
    target_file = dir_path / "sources.yaml"
    if target_file.exists():
        try:
            content = target_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                return SourcesCatalogConfig.model_validate(data)
        except Exception as err:
            logger.warning("Failed parsing %s: %s", target_file, err)

    _ensure_template(dir_path / "sources.yaml.example")
    return SourcesCatalogConfig()
