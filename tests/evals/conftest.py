"""Pytest fixtures for golden dataset evaluations with enriched SQLite test vault and real ReAct engine."""

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
    """Provide an isolated SQLite database initialized with 12 knowledge notes and 5 raw signals."""
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
    asyncio.run(
        store.upsert_source_state(
            SourceState(id="kernel_org", source_type="rss", url_or_path="https://kernel.org/feeds")
        )
    )

    # 12 Realistic Knowledge Notes
    notes = [
        # 1. Architecture WAL
        KnowledgeNote(
            id="note_arch_wal",
            slug="2026-10-01_ekko-sqlite-wal-architecture",
            title="Ekko SQLite WAL Architecture",
            summary="Architecture de stockage local-first avec SQLite en mode WAL et transactions concurrentes.",
            content=(
                "Ekko utilise SQLite configuré en mode WAL (Write-Ahead Logging) pour garantir des lectures non bloquantes "
                "pendant les écritures. Le timeout busy_timeout est fixé à 10000 ms pour résister à la contention concurrente. "
                "Les transactions sont strictement gérées via un context manager assurant un commit déterministe."
            ),
            tags=["architecture", "sqlite", "wal"],
            sources=["internal_architecture"],
            created_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
        ),
        # 2. IPC Unix Sockets
        KnowledgeNote(
            id="note_ipc_sockets",
            slug="2026-10-02_performances-ipc-unix-sockets",
            title="Performances IPC Unix Sockets",
            summary="Benchmark et latence des communications inter-processus par sockets de domaine Unix.",
            content=(
                "Les benchmarks IPC sur Linux démontrent une latence sub-milliseconde (0.3 ms par requête aller-retour) "
                "en utilisant les sockets UNIX de domaine /tmp/ekko.sock avec le protocole JSON-RPC 2.0 et streaming NDJSON. "
                "Le débit mémoire dépasse 450 Mo/s sans surcharge TCP."
            ),
            tags=["system", "linux", "ipc"],
            sources=["linux_benchmarks"],
            created_at=datetime(2026, 10, 2, 11, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 2, 11, 0, tzinfo=timezone.utc),
        ),
        # 3. Zero-Copy IPC
        KnowledgeNote(
            id="note_zerocopy_ipc",
            slug="2026-10-03_zero-copy-memory-shared-buffers",
            title="Zero-Copy Memory & Shared Buffers",
            summary="Gestion de tampons mémoire partagée sans copie pour le transfert de gros volumes de données.",
            content=(
                "La technique de mémoire partagée POSIX (shm_open, mmap) permet d'éliminer les copies mémoires inter-processus. "
                "En évitant les allers-retours entre l'espace utilisateur et le noyau, le CPU conserve son cache L1/L2 intact."
            ),
            tags=["system", "memory", "performance"],
            sources=["os_internals"],
            created_at=datetime(2026, 10, 3, 14, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 3, 14, 0, tzinfo=timezone.utc),
        ),
        # 4. eBPF Tracing
        KnowledgeNote(
            id="note_ebpf_tracing",
            slug="2026-10-04_observabilite-systeme-avec-ebpf",
            title="Observabilité Système avec eBPF",
            summary="Surveillance et profilage haute fidélité du noyau Linux sans modification du code applicatif.",
            content=(
                "Extended Berkeley Packet Filter (eBPF) permet d'exécuter des programmes de traçage vérifiés dans le noyau Linux. "
                "Grâce aux sondes kprobes et tracepoints, eBPF capture les appels système I/O et réseau avec un overhead inférieur à 1%."
            ),
            tags=["linux", "kernel", "ebpf"],
            sources=["kernel_observability"],
            created_at=datetime(2026, 10, 4, 16, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 4, 16, 0, tzinfo=timezone.utc),
        ),
        # 5. Transformers
        KnowledgeNote(
            id="note_transformers_core",
            slug="2026-10-05_architecture-et-mecanismes-des-transformers",
            title="Architecture et Mécanismes des Transformers",
            summary="Principes de base du mécanisme d'auto-attention et couches feed-forward des Transformers.",
            content=(
                "L'architecture Transformer repose sur le calcul de produit scalaire mis à l'échelle softmax(QK^T / sqrt(d_k))V. "
                "L'attention multi-têtes (Multi-Head Attention) permet de capturer simultanément des relations contextuelles distinctes. "
                "La normalisation de couche (LayerNorm) et les connexions résiduelles évitent la disparition du gradient."
            ),
            tags=["ia", "deeplearning", "nlp"],
            sources=["vaswani_2017"],
            created_at=datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc),
        ),
        # 6. LoRA Fine-Tuning
        KnowledgeNote(
            id="note_lora_finetuning",
            slug="2026-10-06_adaptation-efficace-des-modeles-avec-lora",
            title="Adaptation Efficace des Modèles avec LoRA",
            summary="Fine-tuning économe en paramètres via la décomposition de matrices en rang réduit.",
            content=(
                "Low-Rank Adaptation (LoRA) gèle les poids pré-entraînés du modèle W_0 et injecte deux matrices entraînables A et B "
                "de rang r tel que delta_W = B x A. Cela réduit le nombre de paramètres entraînables de plus de 99% et permet de "
                "conserver une empreinte VRAM minimale lors de l'adaptation de modèles 7B ou 14B."
            ),
            tags=["ia", "finetuning", "lora"],
            sources=["hu_2021_lora"],
            created_at=datetime(2026, 10, 6, 11, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 6, 11, 0, tzinfo=timezone.utc),
        ),
        # 7. RAG vs GraphRAG
        KnowledgeNote(
            id="note_rag_vs_graphrag",
            slug="2026-10-07_comparatif-rag-classique-vs-graphrag",
            title="Comparatif RAG Classique vs GraphRAG",
            summary="Analyse comparative entre chunking vectoriel dense et graphes de connaissances hiérarchiques.",
            content=(
                "Le RAG standard excelle pour retrouver des passages précis via similarité dense ou BM25. "
                "GraphRAG extrait au préalable des entités et relations pour construire un graphe de connaissances, "
                "permettant de répondre à des questions holistiques et globales sur de volumineux corpus documentaires."
            ),
            tags=["rag", "knowledge-graph", "search"],
            sources=["msft_graphrag"],
            created_at=datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc),
        ),
        # 8. Quantification 4-bit
        KnowledgeNote(
            id="note_quantization_4bit",
            slug="2026-10-08_quantification-4bit-awq-et-gptq",
            title="Quantification 4-bit (AWQ et GPTQ)",
            summary="Méthodes de compression post-entraînement pour l'inférence locale de LLM sur GPU grand public.",
            content=(
                "AWQ (Activation-aware Weight Quantization) protège les 1% de poids saillants en observant la distribution "
                "des activations, préservant ainsi la perplexité. GPTQ applique une quantification basée sur l'inverse de la matrice hessienne. "
                "Ces approches réduisent la consommation mémoire d'un modèle 7B de 14 Go à environ 4.5 Go de VRAM."
            ),
            tags=["quantization", "vram", "llm"],
            sources=["tinyml_quant"],
            created_at=datetime(2026, 10, 8, 15, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 8, 15, 0, tzinfo=timezone.utc),
        ),
        # 9. Rust Memory Model
        KnowledgeNote(
            id="note_rust_memory",
            slug="2026-10-09_modele-de-memoire-et-ownership-en-rust",
            title="Modèle de Mémoire et Ownership en Rust",
            summary="Garanties de sûreté mémoire à la compilation via l'Ownership, le Borrowing et les Lifetimes.",
            content=(
                "Rust assure la sûreté mémoire sans ramasse-miettes grâce à son système de possession (Ownership). "
                "Chaque valeur a un propriétaire unique ; les emprunts mutables sont exclusifs (&mut T vs &T). "
                "Le compilateur élimine statiquement les data races et les pointeurs sauvages (use-after-free)."
            ),
            tags=["rust", "systems", "security"],
            sources=["rust_book"],
            created_at=datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc),
        ),
        # 10. Pydantic v2 Core
        KnowledgeNote(
            id="note_pydantic_v2",
            slug="2026-10-10_optimisations-pydantic-v2-core",
            title="Optimisations Pydantic v2 Core",
            summary="Accélération de la validation et désérialisation de données Python grâce au moteur pydantic-core en Rust.",
            content=(
                "Pydantic v2 délègue la validation de types et la sérialisation JSON à la bibliothèque native pydantic-core rédigée en Rust. "
                "Les performances d'instanciation de modèles sont multipliées par 5 à 15 par rapport à Pydantic v1. "
                "Le support de TypeAdapter et des discriminateurs stricts permet un parsing polymorphique ultra-rapide."
            ),
            tags=["python", "pydantic", "validation"],
            sources=["pydantic_docs"],
            created_at=datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc),
        ),
        # 11. FastEmbed & ONNX CPU
        KnowledgeNote(
            id="note_fastembed_onnx",
            slug="2026-10-11_fastembed-et-runtime-onnx-cpu",
            title="FastEmbed et Runtime ONNX CPU",
            summary="Génération locale d'embeddings vectoriels sans dépendance PyTorch lourde ni allocation GPU.",
            content=(
                "FastEmbed utilise le runtime ONNX Runtime avec quantification INT8 pour calculer des embeddings denses sur CPU. "
                "Le modèle bge-small-en-v1.5 génère des vecteurs de dimension 384 en quelques millisecondes sans occuper la mémoire VRAM GPU. "
                "L'empreinte mémoire totale du processus reste inférieure à 120 Mo."
            ),
            tags=["embeddings", "onnx", "frugality"],
            sources=["qdrant_fastembed"],
            created_at=datetime(2026, 10, 11, 14, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 11, 14, 0, tzinfo=timezone.utc),
        ),
        # 12. SQLite-vec & RRF
        KnowledgeNote(
            id="note_sqlite_vec_rrf",
            slug="2026-10-12_fusion-rrf-et-sqlite-vec",
            title="Fusion RRF et sqlite-vec",
            summary="Recherche hybride alliant classement lexical BM25 et distance vectorielle avec Reciprocal Rank Fusion.",
            content=(
                "Ekko implémente l'algorithme RRF (Reciprocal Rank Fusion, k=60) pour réconcilier les rangs issus de SQLite FTS5 (BM25) "
                "et de l'extension sqlite-vec (distance vectorielle cosinus). La fusion équilibre la précision des mots-clés exacts "
                "avec la généralisation sémantique des plongements vectoriels."
            ),
            tags=["search", "vector", "sqlite"],
            sources=["ir_hybrid_search"],
            created_at=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc),
        ),
    ]

    for note in notes:
        asyncio.run(store.save_knowledge_note(note, embedding=[0.0] * 384))

    # 5 Raw Signals (2 retained, 2 pending, 1 archived)
    signals = [
        # Retained 1
        RawSignal(
            id="sig_mistral_large4",
            source_id="hn_tech",
            title="Mistral Large 4 Release and Benchmarks",
            url="https://example.com/mistral-large-4",
            raw_content="Mistral AI présente Mistral Large 4 avec un score MMLU de 88.5% et des capacités de raisonnement natives.",
            clean_content="Mistral AI présente Mistral Large 4 avec un score MMLU de 88.5% et des capacités de raisonnement natives.",
            status=SignalStatus.RETAINED,
            ingested_at=datetime(2026, 10, 13, 8, 0, tzinfo=timezone.utc),
        ),
        # Retained 2
        RawSignal(
            id="sig_deepseek_v3",
            source_id="arxiv_ai",
            title="DeepSeek-V3 MoE Architecture Details",
            url="https://example.com/deepseek-v3",
            raw_content="DeepSeek dévoile son modèle V3 basé sur une architecture Mixture-of-Experts avec 671 milliards de paramètres.",
            clean_content="DeepSeek dévoile son modèle V3 basé sur une architecture Mixture-of-Experts avec 671 milliards de paramètres.",
            status=SignalStatus.RETAINED,
            ingested_at=datetime(2026, 10, 13, 8, 30, tzinfo=timezone.utc),
        ),
        # Pending 1
        RawSignal(
            id="sig_qwen_coder",
            source_id="hn_tech",
            title="Qwen 2.5 Coder 32B Benchmark",
            url="https://example.com/qwen-coder",
            raw_content="Évaluation des capacités de complétion de code et refactoring de Qwen 2.5 Coder 32B sur HumanEval.",
            clean_content="Évaluation des capacités de complétion de code et refactoring de Qwen 2.5 Coder 32B sur HumanEval.",
            status=SignalStatus.PENDING,
            ingested_at=datetime(2026, 10, 13, 9, 0, tzinfo=timezone.utc),
        ),
        # Pending 2
        RawSignal(
            id="sig_kernel_612",
            source_id="kernel_org",
            title="Linux 6.12 Real-Time PREEMPT_RT",
            url="https://example.com/linux-6-12",
            raw_content="Le support temps réel complet PREEMPT_RT est officiellement intégré dans la branche principale du noyau Linux 6.12.",
            clean_content="Le support temps réel complet PREEMPT_RT est officiellement intégré dans la branche principale du noyau Linux 6.12.",
            status=SignalStatus.PENDING,
            ingested_at=datetime(2026, 10, 13, 9, 30, tzinfo=timezone.utc),
        ),
        # Archived
        RawSignal(
            id="sig_legacy_archive",
            source_id="hn_tech",
            title="Legacy LLM Tool Calling Survey 2024",
            url="https://example.com/legacy-survey",
            raw_content="Revue historique des premiers protocoles de function calling pour modèles de langage fermés.",
            clean_content="Revue historique des premiers protocoles de function calling pour modèles de langage fermés.",
            status=SignalStatus.ARCHIVED,
            ingested_at=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
        ),
    ]

    asyncio.run(store.save_raw_signals(signals))

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
