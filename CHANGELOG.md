# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0-beta] - 2026-10-14

### Added
- **Tri-State Adaptive Geometry**:
  - `32px` Mini-Capsule mode unblocking 100% of desktop click targets beneath the notch.
  - `230px` Compact mode for Home and Radar views.
  - `460px` Extended mode for Buffer note exploration and Settings.
  - Dual control buttons in header: Collapse `[ — ]` and Close `[ ✕ ]`.
  - Anti-spam transition lock preventing concurrent clicks and race conditions.
- **OS-Aware Chromatic Anomaly**:
  - Dynamic host status bar color sampling (`--notch-anchor`).
  - Seamless vertical background gradient matching Linux GNOME, macOS, and Windows panels.
  - SVG concave fillets with dynamic anchor color blending.
- **Mascot Reactivity & FLIP Morphing**:
  - Pure SVG vector mascot decoupled from fixed dimensions (`viewBox="0 0 100 100"`).
  - Shared layout transition via Framer Motion (`layoutId="app-mascot"`) morphing between `32px` mini capsule (`w-6 h-6`) and `230px` home stage (`w-24 h-24`).
  - 7 micro-emotions: `idle`, `welcome`, `hover_drop`, `ingesting`, `ready`, `alert`, and `error`.
  - Realistic gaze tracking towards incoming cursor drag events and top-left Radar sentinel icon during alerts.
- **Unified Settings View**:
  - Streamlined single-screen configuration replacing legacy tabs.
  - Distillation language toggle (`English` / `Français`).
  - Real-time radar topic tag management and source switches.
- **Playwright E2E Test Suite**:
  - 9 automated end-to-end tests covering geometry, sentinel lifecycle, mascot neutrality, 60 FPS framerate, rapid-click anti-race conditions, memory leak soak tests, and mini-capsule transitions.

### Changed
- **UI Localization**: Harmonized the entire user interface into native English.
- **Production Hardening**:
  - Stripped native Electron menu bar (`Menu.setApplicationMenu(null)`).
  - Restricted DevTools opening strictly to `--debug` flag.
  - Intercepted and disabled `F12`, `Ctrl+Shift+I`, and `Ctrl+R` / `F5` in production builds.
  - Automatically dropped all `console` and `debugger` statements via esbuild in production.
  - Disabled sourcemaps in production builds.

### Removed
- **Legacy CLI REPL**: Completely purged the command-line REPL and legacy terminal prompt interface.
- **Legacy ReAct Chat**: Removed the conversational chat tab and multi-turn ReAct loop in favor of the focused Home/Radar/Buffer reflex triptych.
- **Root Documentation Sprawl**: Removed `ARCHITECTURE.md`, `FRONTEND_ARCHITECTURE.md`, `VISION.md`, and `DESIGN_SYSTEM.md` from the project root; unified all documentation under `docs/`.

---

## [0.1.0-alpha] - 2026-10-09

### Added
- **Initial Python Daemon**:
  - Asynchronous UNIX domain socket server listening at `/tmp/ekko.sock`.
  - Ingestion coordinator with polite scheduling for RSS and REST sources.
  - Local SQLite storage with WAL mode, FTS5 full-text search, and vector embeddings (`sqlite-vec`).
  - Hybrid search retrieval using Reciprocal Rank Fusion ($k=60$).
  - Distillation pipeline powered by LiteLLM supporting Gemini and local Ollama models.
- **Desktop Notch Prototype**:
  - Frameless, top-docked Electron window prototype with transparent margins.
  - Initial drag-and-drop zone for file and URL ingestion.
