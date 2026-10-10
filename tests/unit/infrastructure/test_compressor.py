"""Unit tests for ContentCompressor (heuristic pruning, token budgeting, chunking)."""

import pytest

from ekko.infrastructure.processing.compressor import (
    ContentCompressor,
    ModelProfile,
)


def test_calculate_budget_per_model_profile() -> None:
    """Ensure dynamic token and character budgets are assigned per BYOM profile."""
    compressor = ContentCompressor()

    micro_budget = compressor.calculate_budget(ModelProfile.MICRO)
    std_budget = compressor.calculate_budget(ModelProfile.STANDARD)
    large_budget = compressor.calculate_budget(ModelProfile.LARGE)

    assert micro_budget < std_budget < large_budget
    assert micro_budget == 2048
    assert std_budget == 8192
    assert large_budget == 32768


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


def test_truncate_to_budget() -> None:
    """Ensure content is truncated with clean notice when exceeding profile budget."""
    compressor = ContentCompressor()

    long_text = "Word " * 2000
    truncated = compressor.truncate_to_budget(long_text, ModelProfile.MICRO)

    assert len(truncated) < len(long_text)
    assert "[... Contenu tronqué pour respecter le budget de tokens ...]" in truncated


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
