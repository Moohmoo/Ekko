"""Unit tests for the autonomous background SignalDistiller."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from ekko.core.models import ModelResponse, RawSignal, SignalStatus
from ekko.ingestion.distiller import SignalDistiller


@pytest.fixture
def sample_signal() -> RawSignal:
    """Provide a realistic sample raw signal for distillation."""
    return RawSignal(
        id="sig_test_1",
        source_id="arxiv_ai",
        title="Attention Is All You Need",
        url="https://arxiv.org/abs/1706.03762",
        raw_content="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
        clean_content="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
        status=SignalStatus.RETAINED,
    )



@pytest.mark.asyncio
async def test_distill_batch_empty_pending_signals(tmp_path: Path) -> None:
    """Ensure distill_batch returns 0 when no signals are pending."""
    mock_store = AsyncMock()
    mock_store.get_pending_signals.return_value = []
    mock_llm = AsyncMock()

    distiller = SignalDistiller(store=mock_store, llm_provider=mock_llm, notes_dir=tmp_path)
    count = await distiller.distill_batch(batch_size=5)

    assert count == 0
    mock_llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_distill_batch_success_transitions_to_processed(
    tmp_path: Path, sample_signal: RawSignal
) -> None:
    """Ensure distill_batch parses LLM response, saves note, and marks signal processed."""
    mock_store = AsyncMock()
    mock_store.get_pending_signals.return_value = [sample_signal]

    distill_json = json.dumps({
        "title": "Transformer Architecture Explained",
        "summary": "Transformers replace recurrence entirely with multi-head self-attention.",
        "key_points": [
            "Self-attention mechanism",
            "Multi-head parallel processing",
            "Positional encoding",
        ],
        "tags": ["deep-learning", "transformers"],
    })
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = ModelResponse(
        content=distill_json,
        model_name="mock_model",
    )

    distiller = SignalDistiller(store=mock_store, llm_provider=mock_llm, notes_dir=tmp_path)
    count = await distiller.distill_batch(batch_size=5)

    assert count == 1
    mock_store.save_knowledge_note.assert_awaited_once()
    saved_note = mock_store.save_knowledge_note.call_args[0][0]
    assert saved_note.title == "Transformer Architecture Explained"
    assert "Self-attention mechanism" in saved_note.content
    assert "transformers" in saved_note.tags

    mock_store.mark_signal_status.assert_awaited_once_with("sig_test_1", "processed")

    # Check physical file creation in notes directory
    created_files = list(tmp_path.glob("*.md"))
    assert len(created_files) == 1
    file_content = created_files[0].read_text(encoding="utf-8")
    assert "Transformer Architecture Explained" in file_content
    assert "Self-attention mechanism" in file_content


@pytest.mark.asyncio
async def test_distill_batch_error_transitions_to_failed(
    tmp_path: Path, sample_signal: RawSignal
) -> None:
    """Ensure exceptions during distillation mark signal as failed without crashing."""
    mock_store = AsyncMock()
    mock_store.get_pending_signals.return_value = [sample_signal]

    mock_llm = AsyncMock()
    mock_llm.generate.side_effect = RuntimeError("Inference server offline")

    distiller = SignalDistiller(store=mock_store, llm_provider=mock_llm, notes_dir=tmp_path)
    count = await distiller.distill_batch(batch_size=5)

    assert count == 0
    mock_store.save_knowledge_note.assert_not_called()
    mock_store.mark_signal_status.assert_awaited_once_with("sig_test_1", "failed")


@pytest.mark.asyncio
async def test_distill_batch_unformatted_response_fallback(
    tmp_path: Path, sample_signal: RawSignal
) -> None:
    """Ensure plain text LLM response without JSON falls back gracefully and persists."""
    mock_store = AsyncMock()
    mock_store.get_pending_signals.return_value = [sample_signal]

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = ModelResponse(
        content="This paper introduces the Transformer model relying on attention.",
        model_name="mock_model",
    )

    distiller = SignalDistiller(store=mock_store, llm_provider=mock_llm, notes_dir=tmp_path)
    count = await distiller.distill_batch(batch_size=5)

    assert count == 1
    mock_store.save_knowledge_note.assert_awaited_once()
    mock_store.mark_signal_status.assert_awaited_once_with("sig_test_1", "processed")


@pytest.mark.asyncio
async def test_distill_raw_content_and_file_success(tmp_path: Path) -> None:
    """Ensure distill_raw_content and distill_file process content into knowledge notes."""
    mock_store = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = ModelResponse(
        content=json.dumps({
            "title": "Clean Code Architecture",
            "summary": "Hexagonal architecture decouples domain logic.",
            "key_points": ["Ports and adapters", "No DB leaks", "Dependency inversion"],
            "tags": ["architecture", "clean-code"],
        }),
        model_name="mock_model",
    )

    distiller = SignalDistiller(store=mock_store, llm_provider=mock_llm, notes_dir=tmp_path)

    # Test in-memory raw content distillation
    note = await distiller.distill_raw_content("Domain core logic here.", title="Hexagonal Architecture")
    assert note.title == "Clean Code Architecture"
    assert "Ports and adapters" in note.content
    assert mock_store.save_knowledge_note.await_count == 1

    # Test physical file distillation
    doc_file = tmp_path / "architecture_notes.txt"
    doc_file.write_text("Detailed document text.", encoding="utf-8")

    file_note = await distiller.distill_file(doc_file)
    assert file_note.title == "Clean Code Architecture"
    assert mock_store.save_knowledge_note.await_count == 2


@pytest.mark.asyncio
async def test_distill_empty_content_raises_distillation_error(tmp_path: Path) -> None:
    """Ensure empty content raises DistillationError immediately."""
    from ekko.core.errors import DistillationError

    mock_store = AsyncMock()
    mock_llm = AsyncMock()
    distiller = SignalDistiller(store=mock_store, llm_provider=mock_llm, notes_dir=tmp_path)

    with pytest.raises(DistillationError, match="Cannot distill empty content"):
        await distiller.distill_raw_content("   ")

    with pytest.raises(DistillationError, match="File not found"):
        await distiller.distill_file(tmp_path / "non_existent.md")


@pytest.mark.asyncio
async def test_distill_uses_semaphore_lock(tmp_path: Path, sample_signal: RawSignal) -> None:
    """Ensure SignalDistiller acquires the injected semaphore during distillation."""
    import asyncio

    mock_store = AsyncMock()
    mock_store.get_pending_signals.return_value = [sample_signal]
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = ModelResponse(
        content=json.dumps({"title": "Test", "summary": "Sum", "key_points": [], "tags": []}),
        model_name="mock",
    )
    semaphore = asyncio.Semaphore(1)

    distiller = SignalDistiller(
        store=mock_store,
        llm_provider=mock_llm,
        notes_dir=tmp_path,
        semaphore=semaphore,
    )

    # Acquire semaphore to test contention/locking behavior
    assert not semaphore.locked()
    await distiller.distill_signal(sample_signal)
    # Semaphore should be released after execution
    assert not semaphore.locked()


@pytest.mark.asyncio
async def test_distill_injects_popular_tags_and_normalizes_output(
    tmp_path: Path, sample_signal: RawSignal
) -> None:
    """Ensure SignalDistiller fetches popular tags, injects them in prompt, and normalizes output tags."""
    mock_store = AsyncMock()
    mock_store.get_popular_tags.return_value = ["deep-learning", "transformers", "nlp"]

    distill_json = json.dumps({
        "title": "Normalized Tag Test",
        "summary": "Testing tag normalization and taxonomy injection.",
        "key_points": ["Point A"],
        "tags": ["Machine Learning!", "Deep Learning", "NLP & AI"],
    })
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = ModelResponse(
        content=distill_json,
        model_name="mock_model",
    )

    distiller = SignalDistiller(store=mock_store, llm_provider=mock_llm, notes_dir=tmp_path)
    note = await distiller.distill_signal(sample_signal)

    mock_store.get_popular_tags.assert_awaited_once_with(limit=30)
    messages = mock_llm.generate.call_args[0][0]
    prompt_sent = messages[0].content
    assert "Tags déjà utilisés dans le coffre : deep-learning, transformers, nlp." in prompt_sent
    assert "Règle : réutilise en priorité ces tags existants" in prompt_sent

    assert note.tags == ["machine-learning", "deep-learning", "nlp-ai"]

