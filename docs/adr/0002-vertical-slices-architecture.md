# ADR 0002: Vertical Slices Architecture for Backend Daemon

## Status
Accepted

## Context
Traditional horizontal layering (`controllers`, `services`, `repositories`) forced developers to modify multiple directories for any single feature change. This high coupling slowed iteration on autonomous features like Radar triage, staging buffer, and ingestion connectors.

## Decision
We organize the Python daemon into autonomous vertical slices grouped by business capability (`domains/radar`, `domains/buffer`, `domains/ingestion`, `domains/system`). Slices manage their own domain logic and communicate with shared infrastructure only through explicit contracts.

## Consequences
- High cohesion: all code, schemas, and helpers for a feature live together.
- Independent evolution: changes to one domain slice do not ripple across the codebase.
- Shared utilities and ports must be intentionally governed in `core/` to prevent duplication.
