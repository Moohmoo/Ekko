"""Integration test verifying configuration loading and persistence."""

from pathlib import Path
import yaml

from ekko.domains.system.loader import (
    load_sources_config,
    load_user_context,
)


def test_full_context_loading(tmp_path: Path) -> None:
    """Ensure system domain integrates loaded user context configuration properly."""
    user_yaml = tmp_path / "user_context.yaml"
    user_yaml.write_text(
        yaml.safe_dump({
            "user_name": "Bob",
            "preferred_language": "en",
            "preferences": ["Fast answers"],
        }),
        encoding="utf-8",
    )

    user_cfg = load_user_context(tmp_path)
    assert user_cfg.user_name == "Bob"
    assert user_cfg.preferred_language == "en"
    assert "Fast answers" in user_cfg.preferences


def test_load_sources_config_integration() -> None:
    """Ensure declarative sources configuration loads properly from default config dir."""
    catalog = load_sources_config("config")
    assert len(catalog.sources) >= 2
    source_ids = {s.id for s in catalog.sources}
    assert "hn_tech" in source_ids
    assert "arxiv_ai" in source_ids
