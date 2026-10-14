# ADR 0003: Mascot Slot / FLIP Shared Layout Pattern

## Status
Accepted

## Context
With the introduction of the 32px Mini-Capsule mode, the mascot graphic needed to appear in two distinct locations and dimensions:
1. In the **Home stage** at 96x96px (`w-24 h-24`), responding to gaze and drag events.
2. In the **Mini-Capsule** at 24x24px (`w-6 h-6`), serving as an ambient presence badge when the notch is retracted.

Hardcoding positioning or managing separate mascot components created duplicated SVG logic, desynchronized emotional states, and abrupt visual pop-in during window transitions.

## Decision
We decouple the mascot component into a dimension-agnostic, pure vector representation (`viewBox="0 0 100 100"`, `w-full h-full`) and animate its relocation between the capsule and home stage using Framer Motion's FLIP (First, Last, Invert, Play) shared layout engine with a shared identifier:
```tsx
<motion.div layoutId="app-mascot" className="w-full h-full">
  <Mascot emotion={emotion} />
</motion.div>
```

The parent layout provides the bounding container (`w-6 h-6` in `MiniCapsule.tsx` vs `w-24 h-24` in `HomeView.tsx`).

## Consequences
### Positive
- **Single Source of Truth**: Only one `Mascot.tsx` component exists, maintaining its emotional state across view transitions.
- **Fluid Morphing**: The mascot glides and resizes seamlessly across the screen as the notch expands or contracts.
- **Zero Coordinate Math**: Layout calculations are handled entirely by Framer Motion's matrix projection engine.

### Negative
- Requires a small animation window during expand/collapse before the DOM slot is unmounted. Handled by synchronized curtain callbacks in `useViewStore`.
