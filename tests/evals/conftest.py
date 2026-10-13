"""Pytest fixtures for golden dataset evaluations with isolated SQLite database and real ReAct engine."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
import pytest
import yaml

from ekko.config.loader import load_core_prompt, load_plugins_config, load_user_context
from ekko.core.engine import EkkoEngine
from ekko.core.models import KnowledgeNote, RawSignal, SignalStatus, SourceState
from ekko.core.ports import EmbedderPort
from ekko.core.prompt import build_system_prompt
from ekko.memory.hybrid_store import HybridStore
from ekko.memory.in_memory import InMemoryMemory
from ekko.providers.router import LLMRouter
from ekko.settings import Settings
from ekko.tools.catalog import ToolCatalog


class MockEmbedder(EmbedderPort):
    """Deterministic, lightweight embedder returning zero vectors of dimension 384."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 384


@pytest.fixture
def golden_dataset() -> list[dict]:
    """Load golden dataset test scenarios from YAML specification."""
    dataset_path = Path(__file__).parent / "golden_dataset.yaml"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def eval_db(tmp_path: Path) -> Generator[HybridStore, None, None]:
    """Provide an isolated SQLite database initialized with test knowledge notes and raw signals."""
    db_path = tmp_path / "eval_ekko.db"
    embedder = MockEmbedder()
    store = HybridStore(db_path=db_path, embedder=embedder)
    store.init_schema()

    # Create prerequisite source states
    asyncio.run(
        store.upsert_source_state(
            SourceState(id="hn_tech", source_type="api", url_or_path="https://news.ycombinator.com")
        )
    )
    asyncio.run(
        store.upsert_source_state(
            SourceState(id="arxiv_ai", source_type="rss", url_or_path="https://export.arxiv.org/rss/cs.AI")
        )
    )

    # 1. Note: Ekko Architecture Update
    note1 = KnowledgeNote(
        id="note_arch_1",
        slug="2026-10-10_ekko-architecture-update",
        title="Ekko Architecture Update",
        summary="Mise à jour de l'architecture d'Ekko avec stockage local-first SQLite WAL et indexation vectorielle.",
        content=(
            "Ekko utilise une architecture hexagonale avec un mode SQLite WAL pour maximiser la concurrence "
            "des lectures et écritures. La recherche hybride combine BM25 (FTS5) et similarité vectorielle RRF."
        ),
        tags=["architecture", "sqlite"],
        sources=["internal_doc"],
        created_at=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
    )

    # 2. Note: Mise en œuvre des Transformers
    note2 = KnowledgeNote(
        id="note_trans_1",
        slug="2026-10-11_mise-en-oeuvre-des-transformers",
        title="Mise en œuvre des Transformers",
        summary="Principes fondamentaux de l'architecture Transformer et de l'attention multi-têtes.",
        content=(
            "La mise en œuvre des Transformers repose sur les mécanismes d'attention Query-Key-Value et "
            "l'attention multi-têtes (Multi-Head Attention). Les représentations résiduelles stabilisent le gradient."
        ),
        tags=["ia", "deeplearning"],
        sources=["ai_research"],
        created_at=datetime(2026, 10, 11, 14, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 11, 14, 0, tzinfo=timezone.utc),
    )

    # 3. Note: Performances IPC Unix Sockets
    note3 = KnowledgeNote(
        id="note_ipc_1",
        slug="2026-10-12_performances-ipc-unix-sockets",
        title="Performances IPC Unix Sockets",
        summary="Benchmark et latence des communications inter-processus par sockets de domaine Unix.",
        content=(
            "Les mesures de performances des sockets Unix dans Ekko montrent une latence sub-milliseconde "
            "(inférieure à 0.5 ms par requête) avec streaming NDJSON. Le débit atteint 450 Mo/s en mémoire locale."
        ),
        tags=["system", "linux"],
        sources=["benchmark_linux"],
        created_at=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
    )

    # Insert notes with fake embeddings
    for note in [note1, note2, note3]:
        asyncio.run(store.save_knowledge_note(note, embedding=[0.0] * 384))

    # 4. Raw signals (one retained, one pending)
    sig1 = RawSignal(
        id="sig_mistral_1",
        source_id="hn_tech",
        title="Mistral Large 4 Release and Benchmarks",
        url="https://example.com/mistral-large-4",
        raw_content="Mistral AI présente Mistral Large 4 avec un score MMLU record et un support natif du raisonnement.",
        clean_content="Mistral AI présente Mistral Large 4 avec un score MMLU record et un support natif du raisonnement.",
        status=SignalStatus.RETAINED,
        ingested_at=datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc),
    )
    sig2 = RawSignal(
        id="sig_qwen_1",
        source_id="arxiv_ai",
        title="Qwen 2.5 Coding Capabilities",
        url="https://example.com/qwen-2-5",
        raw_content="Analyse des performances du modèle Qwen 2.5 7B sur les benchmarks de programmation.",
        clean_content="Analyse des performances du modèle Qwen 2.5 7B sur les benchmarks de programmation.",
        status=SignalStatus.PENDING,
        ingested_at=datetime(2026, 10, 13, 9, 0, tzinfo=timezone.utc),
    )
    asyncio.run(store.save_raw_signals([sig1, sig2]))

    yield store


@pytest.fixture
def eval_engine(eval_db: HybridStore) -> EkkoEngine:
    """Build a real EkkoEngine instance wired to the eval database and LLM provider."""
    settings = Settings(sqlite_db_path=str(eval_db.db_path))
    core_prompt = load_core_prompt(settings.config_dir)
    user_context = load_user_context(settings.config_dir)
    plugins_config = load_plugins_config(settings.config_dir)
    system_prompt = build_system_prompt(core_prompt, user_context)

    catalog = ToolCatalog(include_defaults=True)
    embedder = MockEmbedder()
    tools = catalog.build_registry(
        plugins_config.enabled_tools,
        db_manager=eval_db,
        embedder=embedder,
    )
    provider = LLMRouter(settings=settings).get_provider()
    memory = InMemoryMemory()

    return EkkoEngine(
        provider=provider,
        memory=memory,
        tools=tools,
        system_prompt=system_prompt,
    )
