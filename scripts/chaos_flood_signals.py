#!/usr/bin/env python3
"""Chaos test script simulating high-frequency signal flooding into Ekko SQLite database.

Injects 30 distinct synthetic signals with 'retained' status in a single rapid burst (< 200ms)
to verify UI backpressure, clamping at 50, and render stability at 60 FPS.
"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import time
import uuid


def chaos_flood(db_path: str | Path = "data/ekko.db", count: int = 30) -> None:
    """Inject a burst of synthetic retained signals into SQLite database."""
    target_db = Path(db_path)
    if not target_db.exists():
        print(f"[Chaos:WARN] Database {target_db} does not exist yet. Please run ekko once.")
        return

    conn = sqlite3.connect(target_db)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    now = datetime.now(timezone.utc).isoformat()
    burst_id = uuid.uuid4().hex[:6]

    print(f"[Chaos:INIT] Starting burst injection of {count} retained signals (Batch #{burst_id})...")
    start_time = time.perf_counter()

    signals_data = []
    for i in range(1, count + 1):
        sig_id = f"sig_chaos_{burst_id}_{i:03d}"
        title = f"Rupture Technologique #{i:02d} — {burst_id.upper()} (Simulation Chaos)"
        url = f"https://chaos-test.local/signals/{burst_id}/{i}"
        summary = (
            f"Synthèse de veille simulée pour le signal #{i}. "
            "Démontre la résilience de l'interface Electron et le plafonnement du buffer."
        )
        source_id = "chaos_tester"
        status = "retained"
        signals_data.append((sig_id, source_id, url, title, summary, summary, summary, now, now, status))

    with conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO source_states (id, source_type, url_or_path, created_at)
            VALUES ('chaos_tester', 'rest_api', 'https://chaos-test.local', ?);
            """,
            (now,),
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO raw_signals (
                id, source_id, url, title, raw_content, clean_content, summary, ingested_at, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            signals_data,
        )

    duration_ms = (time.perf_counter() - start_time) * 1000

    retained_count = conn.execute("SELECT count(*) FROM raw_signals WHERE status = 'retained';").fetchone()[0]
    conn.close()

    print(f"[Chaos:DONE] Injected {count} signals in {duration_ms:.2f} ms (< 200 ms target: {'PASS' if duration_ms < 200 else 'SLOW'}).")
    print(f"[Chaos:STATE] Total retained signals currently in DB: {retained_count}")
    print("[Chaos:INSPECT] Observez l'encoche Electron : l'UI doit rester fluide à 60 FPS sans clignotement.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Chaos test script simulating high-frequency signal flooding.")
    parser.add_argument(
        "--count",
        type=int,
        default=30,
        help="Number of synthetic retained signals to inject (default: 30).",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/ekko.db",
        help="Path to the SQLite database (default: data/ekko.db).",
    )
    args = parser.parse_args()
    chaos_flood(db_path=args.db, count=args.count)
