# ADR 0002: Vertical Slices Architecture for Backend Daemon

## Status
Accepted

## Context
Initial iterations organized the Python daemon in traditional horizontal technical layers (`controllers`, `services`, `repositories`, `models`). As new features (e.g., Radar blindspot triage, Obsidian export, hybrid search) were added, every change required touching four or five distinct directories (shotgun surgery), increasing coupling and cognitive load.

## Decision
We organize the Ekko backend using **Vertical Slices** partitioned by functional domain contexts:
- `domains/ingestion`: Connectors (RSS, REST, arXiv, HackerNews), scheduler, and raw payload normalization.
- `domains/distillation`: Prompt management, LLM distillation, and synthesis pipeline.
- `db`: Database management, migrations, and the hybrid search engine (SQLite WAL + FTS5 + sqlite-vec).
- `daemon`: IPC server, process supervisor, and resource confinement.

Each slice manages its own domain logic, data models, and specialized helpers, interacting with other slices only through explicit contracts and ports.

## Consequences
### Positive
- **High Cohesion**: All code related to an ingestion connector or search ranking lives together.
- **Independent Evolution**: Adding a new signal source or modifying distillation logic does not ripple into the IPC dispatcher or storage manager.
- **Isolated Testing**: Unit and integration tests can execute against a single slice without standing up mock infrastructure for the entire application.

### Negative
- Shared utility logic must be intentionally placed in `core/` to prevent premature duplication between slices.
