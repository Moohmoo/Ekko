"""Integration test verifying full configuration and context loading."""

from pathlib import Path
import yaml

from ekko.domains.system.loader import (
    load_core_prompt,
    load_plugins_config,
    load_sources_config,
    load_user_context,
)


def test_full_context_loading(tmp_path: Path) -> None:
    """Ensure system domain integrates loaded configuration properly."""
    core_yaml = tmp_path / "core_prompt.yaml"
    core_yaml.write_text(
        yaml.safe_dump({
            "identity": "Agent Test",
            "mission": "Deliver value",
            "guardrails": ["Safe execution"],
        }),
        encoding="utf-8",
    )
    user_yaml = tmp_path / "user_context.yaml"
    user_yaml.write_text(
        yaml.safe_dump({
            "user_name": "Bob",
            "preferred_language": "en",
            "preferences": ["Fast answers"],
        }),
        encoding="utf-8",
    )
    plugins_yaml = tmp_path / "plugins.yaml"
    plugins_yaml.write_text(
        yaml.safe_dump({"enabled_tools": ["system_info"]}),
        encoding="utf-8",
    )

    core_cfg = load_core_prompt(tmp_path)
    user_cfg = load_user_context(tmp_path)
    plugins_cfg = load_plugins_config(tmp_path)

    assert core_cfg.identity == "Agent Test"
    assert user_cfg.user_name == "Bob"
    assert "Fast answers" in user_cfg.preferences
    assert plugins_cfg.enabled_tools == ["system_info"]


def test_load_sources_config_integration() -> None:
    """Ensure declarative sources configuration loads properly from default config dir."""
    catalog = load_sources_config("config")
    assert len(catalog.sources) >= 2
    source_ids = {s.id for s in catalog.sources}
    assert "hn_tech" in source_ids
    assert "arxiv_ai" in source_ids
