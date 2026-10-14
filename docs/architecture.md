# System Architecture

Ekko is an ambient cognitive buffer and blind-spot watch sentinel docked directly beneath the host operating system's top panel. It is engineered around a single ergonomic rule: **all interactions must complete in under 3 seconds**.

---

## 1. System Topology

The application is architected into two decoupled tiers communicating over a dedicated local UNIX domain socket using JSON-RPC 2.0 and NDJSON streaming:

```
+-------------------------------------------------------------------------+
|                        ELECTRON CLIENT (DESKTOP)                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                 Renderer Process (React 19 + Vite)                |  |
|  |  [Home: Drop & Last Note]  [Radar: Triage]  [Buffer: Obsidian]    |  |
|  |             Zustand Stores  *  Framer Motion Engine               |  |
|  +---------------------------------+---------------------------------+  |
|                                    | window.ekkoAPI (ContextBridge)     |
|  +---------------------------------v---------------------------------+  |
|  |                      Main Process (Node.js)                       |  |
|  |  * Window Bounds & Geometry      * Top Bar Anchor Detection       |  |
|  |  * Global Shortcuts & System Tray * Daemon Process Lifecycle       |  |
|  +---------------------------------+---------------------------------+  |
+------------------------------------|------------------------------------+
                                     | UNIX Domain Socket (/tmp/ekko.sock)
                                     | JSON-RPC 2.0 / NDJSON Streaming
+------------------------------------v------------------------------------+
|                         EKKO DAEMON (PYTHON 3.14+)                      |
|                                                                         |
|  +-------------------------+  +--------------------------------------+  |
|  |       IPC Server        |  |        Ingestion Coordinator         |  |
|  |  * Socket Dispatcher    |  |  * Polite Polling Scheduler          |  |
|  |  * NDJSON Streamer      |  |  * Connectors (RSS, REST, arXiv, HN) |  |
|  +------------+------------+  +------------------+-------------------+  |
|               |                                  |                      |
|  +------------v----------------------------------v-------------------+  |
|  |                         Domain Slices                             |  |
|  |  * Distiller (LiteLLM Provider: Gemini / Ollama Local)            |  |
|  |  * Resource Confinement (OS Niceness + Semaphores)                |  |
|  +----------------------------+--------------------------------------+  |
|                               |                                         |
|  +----------------------------v--------------------------------------+  |
|  |                    Storage & Retrieval Engine                     |  |
|  |  * SQLite (WAL Mode, synchronous=NORMAL)                          |  |
|  |  * Lexical Search (FTS5 BM25)                                     |  |
|  |  * Dense Vector Search (sqlite-vec + FastEmbed)                   |  |
|  |  * Hybrid Fusion: Reciprocal Rank Fusion (RRF, k=60)              |  |
|  |  * File Exporter: Markdown with Obsidian Frontmatter              |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 2. Window Geometry & Lifecycle

Ekko operates as a frameless, transparent, top-docked window (`resizable: false`, `alwaysOnTop: true`). Its geometry adapts dynamically across three discrete states:

```
+-------------------------------------------------------------------------+
| 1. Mini-Capsule Mode (32px x 130px)                                     |
|    [ (Mascot) * Pending Signals Dot  ^ ]                                |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
| 2. Compact Notch Mode (230px x 660px) -- Home & Radar                   |
|    +---------------------------------------------------------------+    |
|    | Header (32px): Navigation tabs [Home | Radar | Buffer] [ - X ]|    |
|    +---------------------------------------------------------------+    |
|    | Stage (178px):                                                |    |
|    |   - Home: Bento Drop Zone + Reactive Mascot + Last Note Card  |    |
|    |   - Radar: Blindspot Signal Card + Action Bar                 |    |
|    +---------------------------------------------------------------+    |
+-------------------------------------------------------------------------+

+-------------------------------------------------------------------------+
| 3. Extended Mode (460px x 660px) -- Buffer & Settings                   |
|    +---------------------------------------------------------------+    |
|    | Header (32px): Navigation tabs [Home | Radar | Buffer] [ - X ]|    |
|    +---------------------------------------------------------------+    |
|    | Stage (408px):                                                |    |
|    |   - Buffer: Note List + Instant Search + Markdown Viewer      |    |
|    |   - Settings: Distillation Language, Topics, Sources          |    |
|    +---------------------------------------------------------------+    |
+-------------------------------------------------------------------------+
```

### Transition & Curtain Orchestration
- **Expansion (32px -> 230/460px)**: The native Electron window expands immediately via `win.setBounds()`, followed by an unrolling curtain animation rendered by Framer Motion.
- **Collapse (230/460px -> 32px)**: The visual container contracts upward into the capsule shape; `win.setBounds()` is called only after animation completion to prevent desktop clipping.
- **Sentinel Lifecycle**: Pressing `Escape` or clicking `[ ✕ ]` hides the window (`win.hide()`) rather than destroying it, preserving UI state and ensuring instant re-display on hotkey invocation.

---

## 3. Storage & Retrieval Subsystem

The storage architecture is strictly **local-first** and self-contained within a single SQLite database (`data/ekko.db`):

1. **Transaction Engine**:
   - SQLite running in Write-Ahead Logging (`WAL`) mode with `synchronous = NORMAL` and 60-second busy timeouts.
2. **Lexical Retrieval**:
   - SQLite FTS5 virtual table indexing note content, title, tags, and summary with BM25 ranking.
3. **Semantic Retrieval**:
   - Vector embeddings generated locally via FastEmbed (`BAAI/bge-small-en-v1.5` / `bge-small-zh-v1.5`), indexed using the native `sqlite-vec` extension with cosine distance.
4. **Hybrid Rank Fusion (RRF)**:
   - Queries execute against both lexical and vector indices concurrently.
   - Results are unified using Reciprocal Rank Fusion:
     $$\text{RRF Score}(d) = \sum_{m \in \{\text{lexical}, \text{vector}\}} \frac{1}{k + r_m(d)} \quad (k = 60)$$
   - Produces balanced rankings resilient to vocabulary mismatch without requiring external vector databases.
5. **Obsidian Compatibility**:
   - Distilled notes persist as standard Markdown files (`data/notes/*.md`) with complete YAML frontmatter (ID, source, timestamp, tags, summary).

---

## 4. Backend Vertical Slices

The Python daemon (`src/ekko/`) is structured into decoupled domain slices:

- **`domains/ingestion/`**: Declarative polling connectors for RSS, REST, arXiv, and HackerNews with rate-limiting, jitter, and heuristic content extraction.
- **`domains/distillation/`**: Distillation coordinator compressing ingested raw signals into structured atomic notes using LiteLLM (supporting Gemini, Ollama, and OpenAI-compatible endpoints).
- **`db/`**: Schema migrations, transactional connections, and hybrid search implementation.
- **`daemon/`**: UNIX socket server handling client requests, lifecycle management, and resource confinement (process niceness incremented by +10 to ensure zero impact on foreground desktop tasks).
