# Ekko Design System

The Ekko Design System defines the visual language, color tokens, responsive geometry, and mascot motion physics for the Ekko desktop notch under OLED Dark Mode.

---

## 1. Theme & Color Tokens (OLED Dark Mode)

The interface is built for OLED displays, pairing pitch-black surfaces with vibrant blue and cyan accents to blend into the host operating system's top panel.

| Token | Value | Role |
|---|---|---|
| **Base Surface** | `#000000` | Deep OLED black; matches OS top bar background |
| **Stage Surface** | `#0c0c0e` / `#141824` | Elevated surface for cards, drop zones, and note lists |
| **Subtle Border** | `rgba(255, 255, 255, 0.08)` | Minimal dividers for containers and cards |
| **Accent Sky** | `#38bdf8` | Interactive focus, active tabs, and primary controls |
| **Cyan Glow** | `#00f2fe` | Ambient highlights during active ingestion and search |
| **Alert Amber** | `#f59e0b` | Unread radar signal badges and sentinel warnings |
| **Success Emerald** | `#10b981` | Daemon connection status and completion feedback |
| **Error Crimson** | `#ef4444` | Ingestion errors and connection alerts |

### Zero Top Border Rule
The notch connects directly to the desktop top panel. To maintain an organic silhouette, **no top border or top corner radius** is applied:
- Top border: `none`
- Top corner radius: `0`
- Bottom corner radius: `16px` (Capsule) / `24px` (Compact & Extended)

---

## 2. Mascot Reactive Expressions (7 Micro-Emotions)

The central droplet mascot is a pure SVG vector graphic that communicates application state through 7 distinct micro-emotions:

| Emotion | Meaning & State | Visual Reaction |
|---|---|---|
| **`idle`** | Default standby | Gentle breathing cycle, natural eye blinks, relaxed gaze |
| **`welcome`** | Application launch | Friendly wave gesture with right hand, bright open eyes |
| **`hover_drop`** | Drag over drop zone | Eyes track incoming cursor downward, hands ready to receive |
| **`ingesting`** | Processing content | Squash-and-stretch cycle, hands moving inward |
| **`ready`** | Distillation complete | Satisfied expression with gentle affirmative nod |
| **`alert`** | Unread radar signals | Round eyes and attention focused toward the Radar tab |
| **`error`** | Ingestion failure | Subtly tilted head, muted gaze, and minor frown |

- **Gaze Tracking**: In `idle` and `hover_drop`, eyes smoothly follow the cursor relative to the pod center. In `alert`, gaze locks toward the Radar tab icon.

---

## 3. Animation Physics & Shared Layout

All transitions use spring physics in Framer Motion to ensure natural, responsive motion without visual fatigue:

- **Spring Dynamics**: Fluid, overshoot-free springs drive tab switches, expansion curtains, and mascot gestures.
- **Shared Layout (FLIP)**: The mascot smoothly morphs between the 32px Capsule (`24x24px`) and the 230px Compact notch (`96x96px`) using a shared `layoutId="app-mascot"`.
- **60 FPS Budget**: Animations animate only GPU-accelerated properties (`transform` and `opacity`), guaranteeing smooth framerates with zero layout recalculation.
