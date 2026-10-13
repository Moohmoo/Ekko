"""Unit tests for configuration schemas and YAML loader."""

from pathlib import Path
import pytest
import yaml

from ekko.config.loader import (
    load_core_prompt,
    load_plugins_config,
    load_user_context,
)
from ekko.config.schemas import (
    CorePromptConfig,
    PluginsConfig,
    UserContextConfig,
)


def test_core_prompt_schema_defaults() -> None:
    """Ensure CorePromptConfig has sensible identity and guardrails defaults."""
    cfg = CorePromptConfig()
    assert "Ekko" in cfg.identity
    assert len(cfg.guardrails) > 0


def test_load_core_prompt_from_existing_yaml(tmp_path: Path) -> None:
    """Ensure load_core_prompt parses YAML file correctly."""
    data = {
        "identity": "Custom Agent",
        "mission": "Solve bugs",
        "guardrails": ["Be concise", "No leaks"],
    }
    file_path = tmp_path / "core_prompt.yaml"
    file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    loaded = load_core_prompt(tmp_path)
    assert loaded.identity == "Custom Agent"
    assert loaded.mission == "Solve bugs"
    assert loaded.guardrails == ["Be concise", "No leaks"]


def test_load_core_prompt_missing_fallback(tmp_path: Path) -> None:
    """Ensure missing core_prompt.yaml returns default without crashing."""
    loaded = load_core_prompt(tmp_path)
    assert "Ekko" in loaded.identity


def test_load_user_context_from_yaml(tmp_path: Path) -> None:
    """Ensure load_user_context loads user profile attributes."""
    data = {
        "user_name": "Alice",
        "preferred_language": "fr",
        "preferences": ["Dark mode", "Short code snippets"],
        "custom_instructions": "Focus on clean code",
    }
    file_path = tmp_path / "user_context.yaml"
    file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    loaded = load_user_context(tmp_path)
    assert loaded.user_name == "Alice"
    assert loaded.preferred_language == "fr"
    assert len(loaded.preferences) == 2


def test_load_user_context_missing_generates_example(tmp_path: Path) -> None:
    """Ensure missing user_context.yaml returns empty context and creates .example template."""
    loaded = load_user_context(tmp_path)
    assert loaded.user_name is None

    example_file = tmp_path / "user_context.yaml.example"
    assert example_file.exists()
    content = example_file.read_text(encoding="utf-8")
    assert "user_name" in content


def test_load_plugins_config_from_yaml(tmp_path: Path) -> None:
    """Ensure load_plugins_config parses enabled tools list."""
    data = {"enabled_tools": ["system_info", "custom_tool"]}
    file_path = tmp_path / "plugins.yaml"
    file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    loaded = load_plugins_config(tmp_path)
    assert loaded.enabled_tools == ["system_info", "custom_tool"]


def test_load_plugins_config_missing_generates_example(tmp_path: Path) -> None:
    """Ensure missing plugins.yaml returns default and generates .example template."""
    loaded = load_plugins_config(tmp_path)
    assert isinstance(loaded.enabled_tools, list)

    example_file = tmp_path / "plugins.yaml.example"
    assert example_file.exists()
    assert "enabled_tools" in example_file.read_text(encoding="utf-8")


def test_save_user_context_atomic(tmp_path: Path) -> None:
    """Ensure save_user_context writes atomically and can be read back cleanly."""
    from ekko.config.loader import save_user_context, load_user_context

    ctx = UserContextConfig(
        user_name="Bob",
        preferred_language="en",
        preferences=["Testing atomic save"],
    )
    saved_path = save_user_context(ctx, config_dir=tmp_path)
    assert saved_path.exists()

    reloaded = load_user_context(tmp_path)
    assert reloaded.user_name == "Bob"
    assert reloaded.preferred_language == "en"
    assert reloaded.preferences == ["Testing atomic save"]


def test_save_sources_config_atomic(tmp_path: Path) -> None:
    """Ensure save_sources_config writes atomically and can be read back cleanly."""
    from ekko.config.loader import save_sources_config, load_sources_config
    from ekko.config.schemas import SourceConfig, SourcesCatalogConfig

    catalog = SourcesCatalogConfig(
        sources=[
            SourceConfig(id="test_feed", type="rss", url="https://example.com/rss", interval="1h"),
        ]
    )
    saved_path = save_sources_config(catalog, config_dir=tmp_path)
    assert saved_path.exists()

    reloaded = load_sources_config(tmp_path)
    assert len(reloaded.sources) == 1
    assert reloaded.sources[0].id == "test_feed"
    assert reloaded.sources[0].interval == "1h"

