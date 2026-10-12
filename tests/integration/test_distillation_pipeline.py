"""Integration test verifying end-to-end background signal distillation and hybrid persistence."""

import json
from pathlib import Path
from unittest.mock import AsyncMock
import pytest

from ekko.core.models import ModelResponse
from ekko.ingestion.distiller import SignalDistiller
from ekko.memory.hybrid_store import HybridStore
from ekko.memory.models import RawSignal, SignalStatus, SourceState


@pytest.mark.asyncio
async def test_end_to_end_distillation_pipeline(tmp_path: Path) -> None:
    """Ensure raw signal inserted in SQLite is distilled into knowledge note and Markdown file."""
    db_file = tmp_path / "test_pipeline.db"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    store = HybridStore(db_path=db_file)
    store.init_schema()

    # Create prerequisite source state and pending raw signal
    source = SourceState(
        id="arxiv_ai",
        source_type="rss",
        url_or_path="https://export.arxiv.org/rss/cs.AI",
    )
    await store.upsert_source_state(source)

    signal = RawSignal(
        id="sig_int_1",
        source_id="arxiv_ai",
        title="DeepSeek-R1 Technical Report",
        url="https://arxiv.org/abs/2501.12948",
        raw_content="We present DeepSeek-R1, which utilizes large-scale reinforcement learning to develop reasoning behaviors.",
        clean_content="We present DeepSeek-R1, which utilizes large-scale reinforcement learning to develop reasoning behaviors.",
        status=SignalStatus.PENDING,
    )
    await store.save_raw_signals([signal])

    # Check signal is pending initially
    pending_before = await store.get_pending_signals(limit=5)
    assert len(pending_before) == 1
    assert pending_before[0].status == SignalStatus.PENDING

    # Setup mock LLM provider returning structured distillation
    distill_payload = json.dumps({
        "title": "DeepSeek-R1 Reinforcement Learning for Reasoning",
        "summary": "DeepSeek-R1 demonstrates emergent reasoning capabilities through pure RL without supervised fine-tuning.",
        "key_points": [
            "Pure reinforcement learning drives reasoning",
            "Multi-stage post-training pipeline",
            "Open-weights efficiency benchmark",
        ],
        "tags": ["deepseek", "reinforcement-learning", "reasoning"],
    })
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = ModelResponse(
        content=distill_payload,
        model_name="mock_model",
    )

    distiller = SignalDistiller(store=store, llm_provider=mock_llm, notes_dir=notes_dir)

    # Execute distillation batch
    processed_count = await distiller.distill_batch(batch_size=5)
    assert processed_count == 1

    # Verify signal status transitioned to processed in SQLite
    signals_after = await store.get_raw_signals(source_id="arxiv_ai")
    assert len(signals_after) == 1
    assert signals_after[0].status == SignalStatus.PROCESSED

    # Verify pending signals list is now empty
    pending_after = await store.get_pending_signals(limit=5)
    assert len(pending_after) == 0

    # Verify knowledge note was persisted in SQLite
    notes = await store.search_notes(query="DeepSeek reasoning", mode="lexical")
    assert len(notes) >= 1
    retrieved_note, _ = notes[0]
    assert "DeepSeek-R1" in retrieved_note.title
    assert "reinforcement-learning" in retrieved_note.tags

    # Verify physical Markdown file was written to disk
    written_files = list(notes_dir.glob("*.md"))
    assert len(written_files) == 1
    markdown_text = written_files[0].read_text(encoding="utf-8")
    assert "DeepSeek-R1" in markdown_text
    assert "Pure reinforcement learning" in markdown_text
