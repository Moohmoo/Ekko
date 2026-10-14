# Ekko Design System

This document formalizes the visual tokens, adaptive geometry, mascot micro-emotions, and animation physics of the Ekko desktop notch under the **Ekko Design System** (OLED Dark Mode).

---

## 1. Color Palette & Surfaces (OLED Dark Mode)

The UI is optimized for OLED displays, eliminating unnecessary backlight bleed and seamlessly integrating with dark host operating systems.

| Token | Hex / CSS Value | Description & Purpose |
|---|---|---|
| **Base Surface** | `#000000` | Deep OLED black; matches OS top panel background |
| **Stage Surface** | `#0c0c0e` / `#141824` | Elevated inner container housing the view triptych |
| **Subtle Border** | `rgba(255, 255, 255, 0.08)` | Minimal structural divider for containers and cards |
| **Active Border** | `rgba(56, 189, 248, 0.4)` / `#38bdf8` | Interactive hover, drag-and-drop focus, and active tabs |
| **Cyan Glow** | `#00f2fe` | Ambient pulsation aura during high-confidence triage |
| **Electric Sky** | `#38bdf8` | Vector accents, satellite hands, active indicators |
| **Deep Azure** | `#0284c7` to `#1e3a8a` | Vertical gradient for the mascot torso |
| **Amber Alert** | `#f59e0b` / `#fbbf24` | Blindspot sentinel badge, unread signal indicator |
| **Success Emerald** | `#10b981` | Daemon connection indicator, action confirmations |
| **Error Crimson** | `#ef4444` | Daemon disconnection, ingestion errors |

### Zero Top Border Rule
The upper boundary of the notch connects directly to the host OS status bar. To preserve visual continuity, **no top border, outline, or top corner radius** may ever be applied to the topmost boundary of the shell:
```css
border-top: none;
border-top-left-radius: 0;
border-top-right-radius: 0;
```

---

## 2. Adaptive Chromatic Anchor & Geometry

To merge organically with varying OS desktop environments (Ubuntu Yaru Dark, GNOME Adwaita Dark, macOS Notch/Menu Bar, Windows Taskbar), Ekko calculates a dynamic CSS anchor token `--notch-anchor` and applies precise geometric surfaces:

| Surface / Component | Width | Height | Fill / Color Token | Corner Radius & Geometry |
|---|---|---|---|---|
| **Host Panel Junction** | Screen width | System panel height | OS Panel Color (`--notch-anchor`) | Straight horizontal plane (`border-top: none`) |
| **Concave Left Fillet** | 20 px | 20 px | `var(--notch-anchor)` | SVG cubic bezier outer concave curve |
| **Concave Right Fillet** | 20 px | 20 px | `var(--notch-anchor)` | SVG cubic bezier outer concave curve |
| **Mini-Capsule Shell** | 130 px | 32 px | `var(--notch-anchor)` to `#0c0c0e` | `rounded-b-2xl` (`16px` bottom corners) |
| **Compact Notch Shell** | 660 px | 230 px | `var(--notch-anchor)` to `#000000` | `rounded-b-3xl` (`24px` bottom corners) |
| **Extended Notch Shell** | 660 px | 460 px | `var(--notch-anchor)` to `#000000` | `rounded-b-3xl` (`24px` bottom corners) |

1. **Auto-Detection**: On startup, the Electron main process samples the system theme (`gsettings`, desktop environment variables, or platform defaults) and injects the value into the DOM root as `--notch-anchor`.
2. **Vertical Fusion Gradient**:
   ```css
   background: linear-gradient(
     to bottom,
     var(--notch-anchor, #131313) 0%,
     #0c0c0e 45%,
     #000000 100%
   );
   ```
3. **Concave Side Fillets**: Two 20px SVG bezier curves attach to the upper left and upper right flanks of the notch, filled with `var(--notch-anchor)` to produce an organic fluid teardrop junction with the system panel.

---

## 3. Mascot Reactive Expressions (7 Micro-Emotions)

The central mascot is a pure SVG vector graphic rendered inside a flexible container (`viewBox="0 0 100 100"`, `w-full h-full`). It responds to application lifecycle states through 7 reactive micro-emotions:

| Emotion | Visual Expression | Trigger Condition |
|---|---|---|
| **`idle`** | Gentle floating breathing cycle, natural eye blinks (4-7s cadence), relaxed gaze. | Default state awaiting user action. |
| **`welcome`** | Friendly greeting gesture with right satellite hand, bright open eyes. | Application launch transition (1.8s duration). |
| **`hover_drop`** | Eyes tracking mouse cursor downward toward the drop target, hands positioned to receive. | Drag event enters the Bento drop zone. |
| **`ingesting`** | Animated chewing / squash-and-stretch cycles, hands cycling inward. | File or URL ingestion and distillation in progress. |
| **`ready`** | Proud, satisfied expression with gentle affirmative vertical nod. | Note distillation completed successfully. |
| **`alert`** | Surprised round eyes and vertical oval mouth directed toward the Radar tab, amber pulse. | Unresolved blindspot signals awaiting triage in Radar. |
| **`error`** | Slightly tilted head, muted gaze, subtle frown. | Ingestion failure or daemon unreachable. |

### Gaze Tracking Mechanics
In `idle` and `hover_drop`, eye positions update smoothly using CSS variables (`--eye-dx`, `--eye-dy`) driven by cursor movement relative to the pod center. During `alert`, cursor tracking is temporarily overridden with fixed negative offsets targeting the Radar icon `[📡]` in the top-left corner.

---

## 4. Animation Physics & Framer Motion Guidelines

All transitions follow physically-based spring physics to prevent robotic linear easing and visual fatigue:

- **Stage Transitions**: Spring stiffness 300, damping 28, mass 0.8.
- **Micro-interactions (buttons, pills)**: Spring stiffness 400, damping 25.
- **Shared Layout (FLIP)**: The mascot smoothly morphs between the 32px mini capsule (`w-6 h-6`) and the 230px home view (`w-24 h-24`) using `<motion.div layoutId="app-mascot">`.
- **60 FPS Budget**: Animations are strictly constrained to hardware-accelerated CSS properties (`transform` and `opacity`). Zero layout recalculation or DOM reflows are permitted during active tracking.
