"""SQLite unified schema definitions and migrations for Ekko V2."""

INIT_UNIFIED_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_states (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    url_or_path TEXT NOT NULL,
    etag TEXT,
    last_modified TEXT,
    last_polled_at TEXT,
    consecutive_errors INTEGER NOT NULL DEFAULT 0,
    backoff_until TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS raw_signals (
    id TEXT PRIMARY KEY,
    source_id TEXT,
    source_type TEXT,
    source_url TEXT,
    external_id TEXT,
    url TEXT,
    title TEXT NOT NULL,
    raw_content TEXT,
    clean_content TEXT,
    summary TEXT,
    author TEXT,
    published_at TEXT,
    ingested_at TEXT DEFAULT (datetime('now')),
    created_at TEXT DEFAULT (datetime('now')),
    status TEXT NOT NULL CHECK(status IN ('pending', 'processed', 'failed', 'retained', 'discarded', 'archived')),
    FOREIGN KEY (source_id) REFERENCES source_states(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_notes (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL,
    sources TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_raw_signals_source ON raw_signals(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_signals_status ON raw_signals(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_notes_slug ON knowledge_notes(slug);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    note_id UNINDEXED,
    title,
    summary,
    content,
    tags,
    tokenize = 'unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_vectors USING vec0(
    note_id TEXT PRIMARY KEY,
    embedding float[384]
);
"""
