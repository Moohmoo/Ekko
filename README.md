# Ekko

<p align="center">
  <strong>Ambient Cognitive Buffer & Blind-Spot Sentinel</strong><br>
  A distraction-free, local-first companion docked beneath your system status bar.
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> &bull;
  <a href="docs/architecture.md">Architecture</a> &bull;
  <a href="docs/design-system.md">Design System</a> &bull;
  <a href="docs/adr/">Decisions (ADRs)</a> &bull;
  <a href="CHANGELOG.md">Changelog</a>
</p>

---

## What is Ekko?

Ekko lives as an organic notch directly docked under your host operating system's top bar (Linux, macOS, Windows). It serves as an **ambient cognitive buffer**:

- **Instant Reflex Capture (Home)**: Drag and drop files (PDF, code, markdown) or links directly into the notch. Ekko ingests and distills them into atomic notes in seconds without breaking your workflow.
- **Blind-Spot Sentinel (Radar)**: Quietly monitors selected technical sources (arXiv, HackerNews, RSS, REST) in the background. Synthesizes anomalies and signals into high-signal briefings you can triage with one click.
- **Actionable Workbench (Buffer)**: Browse your distilled memory with sub-millisecond hybrid search (FTS5 BM25 + dense vector embeddings) and export notes to your Obsidian vault.
- **The Golden Rule**: Every interaction must take **under 3 seconds**.

---

## Data Flow

```
   Raw Signals                           Distilled Knowledge
 (Web / Drag & Drop)                     (Hybrid Local Store)
        |                                         ^
        v                                         |
+-------------------+      UNIX Socket     +-------------------+
|  Electron Notch   | <==================> |   Ekko Daemon     |
|   (React / UI)    |   /tmp/ekko.sock     |   (Python 3.14)   |
+-------------------+                      +-------------------+
        |                                         |
        | [32px Capsule / 230px Notch]            | [LiteLLM Distiller]
        v                                         v
   User Focus                               Obsidian Vault
 (Uninterrupted)                           (Markdown Notes)
```

---

## Quickstart

Get running in three simple commands:

```bash
# 1. Install all backend and frontend dependencies
make install

# 2. Launch the desktop application and background daemon
make dev

# 3. Execute the full verification suite (Pytest & Playwright E2E)
make test
```

---

## Key Capabilities

- **Tri-State Adaptive Geometry**:
  - **Mini-Capsule (`32px`)**: Discrete status indicator with mascot presence and pending signal dot. Leaves desktop click targets completely free.
  - **Compact Mode (`230px`)**: Default home for drag-and-drop ingestion and radar signal triage.
  - **Extended Mode (`460px`)**: Expands downward for note browsing, full-text search, and configuration.
- **OS-Aware Chromatic Anomaly**: The notch dynamically samples your host system panel color (`--notch-anchor`) to blend seamlessly with GNOME, macOS, or Windows panels via smooth concave SVG fillets.
- **Reactive Vector Mascot**: A 100% SVG companion expressing 7 micro-emotions (`idle`, `welcome`, `hover_drop`, `ingesting`, `ready`, `alert`, `error`) that morphs between capsule and notch states with zero layout jank.
- **Local-First & Private**: Powered by SQLite WAL, local vector embeddings (`sqlite-vec`), and local or cloud LLMs via LiteLLM (Gemini / Ollama). Distilled notes are saved directly as Markdown files with YAML frontmatter.

---

## Documentation

Comprehensive engineering documentation lives in [`docs/`](docs/) :

- **[System Architecture](docs/architecture.md)**: System topology, IPC protocol, window orchestration, and hybrid search mechanics.
- **[Ekko Design System](docs/design-system.md)**: OLED color tokens, adaptive anchor gradients, 7 micro-emotions matrix, and Framer Motion spring physics.
- **[Architecture Decision Records](docs/adr/)**:
  - [ADR 0001: UNIX Domain Socket Over HTTP for Local IPC](docs/adr/0001-unix-socket-over-http.md)
  - [ADR 0002: Vertical Slices Architecture for Backend Daemon](docs/adr/0002-vertical-slices-architecture.md)
  - [ADR 0003: Mascot Slot / FLIP Shared Layout Pattern](docs/adr/0003-mascot-slot-flip-pattern.md)

---

## Project Structure

```
.
├── clients/desktop-electron/  # Electron, React 19, Tailwind CSS, Framer Motion
├── config/                    # Default system prompts, sources, and user context
├── data/                      # Local SQLite database (ekko.db) and Markdown notes
├── docs/                      # Architectural specs, design system, and ADRs
├── src/ekko/                  # Python 3.14 backend daemon & vertical slices
├── tests/                     # Backend unit/integration tests and Playwright E2E
├── Makefile                   # High-level build and development tasks
└── pyproject.toml             # Python package configuration (managed via uv)
```

---

## License

This project is licensed under the [MIT License](LICENSE).
