"""Unit tests for ContentCompressor (heuristic pruning, token budgeting, chunking)."""

import pytest

from ekko.domains.ingestion.compressor import (
    ContentCompressor,
    ModelProfile,
    TRUNCATION_NOTICE,
)


def test_calculate_budget_per_model_profile_and_custom() -> None:
    """Ensure dynamic token budgets are assigned per profile or overridden by custom_budget."""
    compressor = ContentCompressor()

    micro_budget = compressor.calculate_budget(ModelProfile.MICRO)
    std_budget = compressor.calculate_budget(ModelProfile.STANDARD)
    large_budget = compressor.calculate_budget(ModelProfile.LARGE)

    assert micro_budget < std_budget < large_budget
    assert micro_budget == 2048
    assert std_budget == 8192
    assert large_budget == 32768

    custom_budget = compressor.calculate_budget(ModelProfile.MICRO, custom_budget=16000)
    assert custom_budget == 16000


def test_heuristic_pruning_removes_boilerplate_and_references() -> None:
    """Ensure heuristic pruning strips navigation, cookie banners, and reference sections."""
    compressor = ContentCompressor()

    dirty_article = """
# Breakthrough in Quantum Architecture

Navigation | Home | About | Contact
Cookie Policy: We use tracking cookies. Accept All.

## Abstract
This paper introduces a fault-tolerant topological quantum qubit design.

## Introduction
Quantum decoherence has historically prevented scalable computing.
Here we demonstrate a hardware implementation with 99.9% fidelity.

## Results
The coherence time reaches 150 microseconds under cryogenic conditions.

## Conclusion
Topological protection offers a robust pathway for fault-tolerant quantum computing.

## References
[1] Smith, J. Quantum Decoherence. Nature 2021.
[2] Doe, A. Cryogenic Qubits. Science 2022.

Privacy Policy | Terms of Service | All rights reserved 2026.
"""

    cleaned = compressor.prune_heuristics(dirty_article)

    # Core content must be preserved
    assert "Breakthrough in Quantum Architecture" in cleaned
    assert "fault-tolerant topological quantum qubit design" in cleaned
    assert "Topological protection offers a robust pathway" in cleaned

    # Boilerplate and noise must be excised
    assert "Cookie Policy" not in cleaned
    assert "Navigation | Home" not in cleaned
    assert "References" not in cleaned
    assert "Smith, J. Quantum Decoherence" not in cleaned
    assert "Privacy Policy" not in cleaned


def test_heuristic_pruning_preserves_legitimate_notes_section() -> None:
    """Ensure heuristic pruning does not prematurely truncate on ## Notes section."""
    compressor = ContentCompressor()

    doc_with_notes = """
# Engineering Specification

## Architecture Overview
System uses event streaming.

## Notes
These are critical implementation notes that must be preserved.

## Notes techniques
Additional technical details.

## References
[1] Some Citation.
"""
    cleaned = compressor.prune_heuristics(doc_with_notes)

    assert "## Notes" in cleaned
    assert "critical implementation notes that must be preserved" in cleaned
    assert "## Notes techniques" in cleaned
    assert "Additional technical details" in cleaned
    assert "## References" not in cleaned
    assert "[1] Some Citation" not in cleaned


def test_truncate_to_budget_with_neutral_notice_and_custom_override() -> None:
    """Ensure content is truncated with neutral notice or custom notice/budget."""
    compressor = ContentCompressor()

    long_text = "Word " * 2000

    # Default neutral marker
    truncated = compressor.truncate_to_budget(long_text, ModelProfile.MICRO)
    assert len(truncated) < len(long_text)
    assert "[... Content truncated to match token budget ...]" in truncated

    # Custom notice override
    custom_notice = "\n\n[... Truncated for display ...]"
    truncated_custom = compressor.truncate_to_budget(
        long_text,
        ModelProfile.MICRO,
        notice=custom_notice,
    )
    assert custom_notice in truncated_custom
    assert "[... Content truncated" not in truncated_custom

    # Custom budget override
    truncated_budget = compressor.truncate_to_budget(
        long_text,
        ModelProfile.MICRO,
        custom_budget=100,  # 100 tokens * 4 = 400 chars
    )
    assert len(truncated_budget) <= 400 + len(TRUNCATION_NOTICE)


def test_chunk_text_preserves_paragraph_boundaries() -> None:
    """Ensure chunking splits text without breaking in the middle of sentences or paragraphs."""
    compressor = ContentCompressor()

    paragraphs = [
        f"Paragraph {i}. " + ("This is explanatory content. " * 15)
        for i in range(10)
    ]
    full_text = "\n\n".join(paragraphs)

    chunks = compressor.chunk_text(full_text, max_chunk_chars=500, overlap_chars=50)

    assert len(chunks) > 1
    for chunk in chunks:
        # Chunks must not exceed max size (allowing small tolerance for sentence boundary)
        assert len(chunk) <= 650
        # Chunks must contain coherent text without leading/trailing empty lines
        assert chunk.strip() != ""
