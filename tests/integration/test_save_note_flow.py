"""Integration test verifying end-to-end ReAct flow with SaveNoteTool and EkkoEngine."""

from pathlib import Path
from unittest.mock import AsyncMock
import pytest

from ekko.core.engine import EkkoEngine
from ekko.core.models import ModelResponse, ToolCall
from ekko.memory.in_memory import InMemoryMemory
from ekko.tools.registry import ToolRegistry
from ekko.tools.save_note import SaveNoteTool


@pytest.mark.asyncio
async def test_save_note_tool_integration_in_engine(tmp_path: Path) -> None:
    """Ensure engine delegates to SaveNoteTool and physically writes markdown file."""
    registry = ToolRegistry()
    note_tool = SaveNoteTool(notes_dir=tmp_path)
    registry.register(note_tool)

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [
        ModelResponse(
            content="",
            model_name="mock-llm",
            tool_calls=[
                ToolCall(
                    id="call_save_note",
                    name="save_note",
                    arguments={
                        "title": "Mistral Large 4 Architecture",
                        "content": "Analyse complète des benchmarks et capacités de raisonnement natif.",
                        "tags": ["ai", "frontier-models"],
                        "sources": ["https://mistral.ai/news/mistral-large-4/"],
                    },
                )
            ],
        ),
        ModelResponse(
            content="La fiche de synthèse sur Mistral Large 4 a été enregistrée avec succès dans votre dossier de notes.",
            model_name="mock-llm",
        ),
    ]

    memory = InMemoryMemory()
    engine = EkkoEngine(
        provider=mock_provider,
        memory=memory,
        tools=registry,
        max_iterations=5,
    )

    user_prompt = "Enregistre une fiche de synthèse sur l'architecture de Mistral Large 4 avec les sources associées."
    reply = await engine.process_message(user_prompt)

    assert "enregistrée avec succès" in reply
    messages = await memory.get_messages("default")
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[2].role == "tool"
    assert messages[2].tool_call_id == "call_save_note"
    assert "Note enregistrée avec succès sous" in messages[2].content
    assert messages[3].role == "assistant"

    # Physical file verification on disk
    written_files = list(tmp_path.glob("*.md"))
    assert len(written_files) == 1
    target_file = written_files[0]
    assert "mistral-large-4-architecture" in target_file.name

    file_text = target_file.read_text(encoding="utf-8")
    assert 'title: "Mistral Large 4 Architecture"' in file_text
    assert "tags:" in file_text
    assert "- ai" in file_text
    assert "- frontier-models" in file_text
    assert 'sources:' in file_text
    assert '"https://mistral.ai/news/mistral-large-4/"' in file_text
    assert "# Mistral Large 4 Architecture" in file_text
    assert "Analyse complète des benchmarks" in file_text
