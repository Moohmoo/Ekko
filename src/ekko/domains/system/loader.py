"""YAML configuration loader with resilient fallbacks and template generation."""

from pathlib import Path
from typing import Any
import yaml

from ekko.domains.system.schemas import (
    CorePromptConfig,
    PluginsConfig,
    SourcesCatalogConfig,
    UserContextConfig,
)
from ekko.logger import get_logger

logger = get_logger("domains.system.loader")


def _read_yaml(file_path: Path) -> dict[str, Any] | None:
    """Read and parse YAML file safely, returning None on failure."""
    if not file_path.exists():
        return None
    try:
        content = file_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        return parsed if isinstance(parsed, dict) else None
    except Exception as err:
        logger.warning("Failed parsing YAML file %s: %s", file_path, err)
        return None


def _ensure_example_template(example_path: Path, sample_content: str) -> None:
    """Write an example template if it does not already exist."""
    example_path.parent.mkdir(parents=True, exist_ok=True)
    if not example_path.exists():
        example_path.write_text(sample_content, encoding="utf-8")
        logger.info("Generated configuration template: %s", example_path)


def load_core_prompt(config_dir: Path | str) -> CorePromptConfig:
    """Load core prompt configuration or fallback to defaults."""
    dir_path = Path(config_dir)
    data = _read_yaml(dir_path / "core_prompt.yaml")
    if data:
        return CorePromptConfig.model_validate(data)
    return CorePromptConfig()


def load_user_context(config_dir: Path | str) -> UserContextConfig:
    """Load user context configuration, generating template if missing."""
    dir_path = Path(config_dir)
    target = dir_path / "user_context.yaml"
    data = _read_yaml(target)
    if data:
        return UserContextConfig.model_validate(data)

    template = (
        "# User context profile (copy to user_context.yaml and adjust)\n"
        "user_name: Alice\n"
        "preferred_language: fr\n"
        "preferences:\n"
        "  - Direct answers without pleasantries\n"
        "  - Focus on code explanations\n"
        "custom_instructions: null\n"
    )
    _ensure_example_template(dir_path / "user_context.yaml.example", template)
    return UserContextConfig()


def load_plugins_config(config_dir: Path | str) -> PluginsConfig:
    """Load plugins feature flags, generating template if missing."""
    dir_path = Path(config_dir)
    target = dir_path / "plugins.yaml"
    data = _read_yaml(target)
    if data:
        return PluginsConfig.model_validate(data)

    template = (
        "# Active plugins feature flags\n"
        "enabled_tools:\n"
        "  - system_info\n"
    )
    _ensure_example_template(dir_path / "plugins.yaml.example", template)
    return PluginsConfig()


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


def load_sources_config(config_dir: Path | str) -> SourcesCatalogConfig:
    """Load sources.yaml or create example template with resilient fallback."""
    dir_path = Path(config_dir)
    target_file = dir_path / "sources.yaml"
    data = _read_yaml(target_file)
    if data:
        return SourcesCatalogConfig.model_validate(data)

    _ensure_example_template(dir_path / "sources.yaml.example", EXAMPLE_SOURCES_YAML)
    return SourcesCatalogConfig()


def _atomic_write_yaml(target_file: Path, data: dict[str, Any]) -> None:
    """Atomically write YAML data via a temporary sibling file."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target_file.with_name(f".{target_file.name}.tmp")
    content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    temp_file.write_text(content, encoding="utf-8")
    temp_file.replace(target_file)


def save_user_context(data: UserContextConfig, config_dir: Path | str = "config") -> Path:
    """Persist validated user context atomically into user_context.yaml."""
    dir_path = Path(config_dir)
    target_file = dir_path / "user_context.yaml"
    _atomic_write_yaml(target_file, data.model_dump(mode="json"))
    logger.info("Saved user context configuration to %s", target_file)
    return target_file


def save_sources_config(data: SourcesCatalogConfig, config_dir: Path | str = "config") -> Path:
    """Persist validated sources catalog atomically into sources.yaml."""
    dir_path = Path(config_dir)
    target_file = dir_path / "sources.yaml"
    _atomic_write_yaml(target_file, data.model_dump(mode="json"))
    logger.info("Saved sources catalog configuration to %s", target_file)
    return target_file


