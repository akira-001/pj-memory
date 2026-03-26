"""Tests for recall reinforcement."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    (tmp_path / "memory" / "logs").mkdir(parents=True)
    (tmp_path / "cogmem.toml").write_text(
        '[cogmem]\nlogs_dir = "memory/logs"\ndb_path = "memory/vectors.db"\n',
        encoding="utf-8",
    )
    config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
    with MemoryStore(config) as s:
        yield s


class TestSchema:
    def test_new_db_has_recall_columns(self, store):
        """New DB has recall_count=0 and last_recalled=NULL by default."""
        store.conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector) "
            "VALUES ('h1', '2026-03-26', 'test', 0.5, '[]')"
        )
        row = store.conn.execute(
            "SELECT recall_count, last_recalled FROM memories WHERE content_hash = 'h1'"
        ).fetchone()
        assert row["recall_count"] == 0
        assert row["last_recalled"] is None

    def test_existing_db_migration(self, tmp_path):
        """Opening a DB without recall columns adds them via ALTER TABLE."""
        db_path = tmp_path / "memory" / "old.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY, content_hash TEXT UNIQUE,
                date TEXT, content TEXT, arousal REAL, vector BLOB
            )
        """)
        conn.execute("""
            CREATE TABLE indexed_files (
                filename TEXT PRIMARY KEY, indexed_at TEXT, entry_count INTEGER
            )
        """)
        conn.execute(
            "INSERT INTO memories VALUES (1, 'old1', '2026-03-20', 'old entry', 0.7, '[]')"
        )
        conn.commit()
        conn.close()

        (tmp_path / "cogmem.toml").write_text(
            '[cogmem]\nlogs_dir = "memory/logs"\ndb_path = "memory/old.db"\n',
            encoding="utf-8",
        )
        (tmp_path / "memory" / "logs").mkdir(parents=True, exist_ok=True)
        config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
        with MemoryStore(config) as s:
            row = s.conn.execute(
                "SELECT recall_count, last_recalled FROM memories WHERE content_hash = 'old1'"
            ).fetchone()
            assert row["recall_count"] == 0
            assert row["last_recalled"] is None
