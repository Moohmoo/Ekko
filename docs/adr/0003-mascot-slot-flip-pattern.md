# ADR 0003: Mascot Slot / FLIP Shared Layout Pattern

## Status
Accepted

## Context
The mascot must appear in both the 32px Mini-Capsule (`24x24px`) and the 230px Home stage (`96x96px`) without desynchronizing its emotional state. Duplicating SVG code or managing separate component instances caused visual pop-in and complex state syncing during window expansion.

## Decision
We keep a single, dimension-agnostic SVG mascot component and animate its relocation between views using Framer Motion's shared layout engine (`layoutId="app-mascot"`). The parent container supplies the target dimensions while the layout engine smoothly interpolates position and scale.

## Consequences
- Single source of truth for mascot emotional state and gaze tracking across all views.
- Fluid, continuous animation during notch expansion and collapse without manual coordinate math.
- Requires coordinating the animation completion callback before unmounting parent view containers.
