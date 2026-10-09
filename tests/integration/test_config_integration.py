"""Integration test verifying full configuration and context loading into EkkoEngine."""

from pathlib import Path
from unittest.mock import AsyncMock
import pytest
import yaml

from ekko.config.loader import (
    load_core_prompt,
    load_plugins_config,
    load_user_context,
)
from ekko.core.engine import EkkoEngine
from ekko.core.models import Message, ModelResponse
from ekko.core.prompt import build_system_prompt
from ekko.memory.in_memory import InMemoryMemory
from ekko.tools.catalog import ToolCatalog


@pytest.mark.asyncio
async def test_full_context_loading_and_turn_execution(tmp_path: Path) -> None:
    """Ensure engine integrates loaded context into prompts without duplicating it."""
    # Write sample configuration
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

    system_prompt = build_system_prompt(core_cfg, user_cfg)
    assert "User Name: Bob" in system_prompt

    catalog = ToolCatalog(include_defaults=True)
    tools = catalog.build_registry(plugins_cfg.enabled_tools)
    assert tools.get("system_info") is not None

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(content="First answer", model_name="test"),
        ModelResponse(content="Second answer", model_name="test"),
    ]
    memory = InMemoryMemory()
    engine = EkkoEngine(
        provider=mock_provider,
        memory=memory,
        tools=tools,
        system_prompt=system_prompt,
    )

    # First turn
    await engine.process_message("Hello", session_id="test_sess")
    call_1_messages = mock_provider.generate.call_args_list[0][0][0]
    assert call_1_messages[0].role == "system"
    assert "User Name: Bob" in call_1_messages[0].content
    assert call_1_messages[1].role == "user"

    # Second turn: verify system prompt is NOT duplicated
    await engine.process_message("How are you?", session_id="test_sess")
    call_2_messages = mock_provider.generate.call_args_list[1][0][0]
    system_count = sum(1 for m in call_2_messages if m.role == "system")
    assert system_count == 1
    assert call_2_messages[0].role == "system"
