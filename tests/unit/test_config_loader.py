"""Unit tests for configuration schemas and YAML loader."""

from pathlib import Path
import yaml

from ekko.domains.system.loader import (
    load_sources_config,
    load_user_context,
    save_sources_config,
    save_user_context,
)
from ekko.domains.system.contracts import (
    SourceConfig,
    SourcesCatalogConfig,
    UserContextConfig,
)


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


def test_save_user_context_atomic(tmp_path: Path) -> None:
    """Ensure save_user_context writes atomically and can be read back cleanly."""
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
