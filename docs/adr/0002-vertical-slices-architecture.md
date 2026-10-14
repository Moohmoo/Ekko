# ADR 0002: Vertical Slices Architecture for Backend Daemon

## Status
Accepted

## Context
Initial iterations organized the Python daemon in traditional horizontal technical layers (`controllers`, `services`, `repositories`, `models`). As new features (e.g., Radar blindspot triage, Obsidian export, hybrid search) were added, every change required touching four or five distinct directories (shotgun surgery), increasing coupling and cognitive load.

## Decision
We organize the Ekko backend using **Vertical Slices** partitioned by functional domain contexts:
- `domains/radar`: Blindspot signals, alert scoring, and background triage watch box.
- `domains/buffer`: Distilled note cards, staging buffer, and Obsidian Markdown vault persistence.
- `domains/ingestion`: Network polling connectors (RSS, REST, arXiv, HackerNews), scheduler, and raw payload normalization/compression.
- `domains/system`: User context, profile preferences, and YAML configuration loading.
- `db/`: Database connections, schema migrations, lexical indexing (FTS5 BM25), dense vector embeddings (`sqlite-vec`), and Reciprocal Rank Fusion (RRF $k=60$).
- `daemon/`: UNIX domain socket server (`/tmp/ekko.sock`), client RPC dispatcher, process supervisor, and resource confinement.

Each slice manages its own domain logic, data models, and specialized helpers, interacting with other slices only through explicit contracts and ports.

## Consequences
### Positive
- **High Cohesion**: All code related to an ingestion connector, radar signal scoring, or buffer note export lives together.
- **Independent Evolution**: Modifying radar alert heuristics or buffer note formatting does not ripple into the IPC dispatcher or storage manager.
- **Isolated Testing**: Unit and integration tests execute against a single slice without standing up mock infrastructure for the entire application.

### Negative
- Shared utility logic and foundational ports must be intentionally placed in `core/` to prevent premature duplication between slices.
