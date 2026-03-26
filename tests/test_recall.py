"""Tests for recall reinforcement."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.store import MemoryStore
from cognitive_memory.types import SearchResult


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


class TestReinforceRecall:
    def test_increments_count(self, store):
        store.conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector) "
            "VALUES ('h1', '2026-03-26', 'test', 0.5, '[]')"
        )
        store.conn.commit()
        store.reinforce_recall("h1")
        row = store.conn.execute(
            "SELECT recall_count FROM memories WHERE content_hash = 'h1'"
        ).fetchone()
        assert row["recall_count"] == 1

    def test_updates_timestamp(self, store):
        store.conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector) "
            "VALUES ('h1', '2026-03-26', 'test', 0.5, '[]')"
        )
        store.conn.commit()
        store.reinforce_recall("h1")
        row = store.conn.execute(
            "SELECT last_recalled FROM memories WHERE content_hash = 'h1'"
        ).fetchone()
        assert row["last_recalled"] is not None
        assert "2026" in row["last_recalled"]

    def test_boosts_arousal(self, store):
        store.conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector) "
            "VALUES ('h1', '2026-03-26', 'test', 0.5, '[]')"
        )
        store.conn.commit()
        store.reinforce_recall("h1")
        row = store.conn.execute(
            "SELECT arousal FROM memories WHERE content_hash = 'h1'"
        ).fetchone()
        assert row["arousal"] == pytest.approx(0.6)

    def test_arousal_caps_at_1(self, store):
        store.conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector) "
            "VALUES ('h1', '2026-03-26', 'high', 0.95, '[]')"
        )
        store.conn.commit()
        store.reinforce_recall("h1")
        row = store.conn.execute(
            "SELECT arousal FROM memories WHERE content_hash = 'h1'"
        ).fetchone()
        assert row["arousal"] == pytest.approx(1.0)

    def test_multiple_recalls(self, store):
        store.conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector) "
            "VALUES ('h1', '2026-03-26', 'repeated', 0.5, '[]')"
        )
        store.conn.commit()
        for _ in range(3):
            store.reinforce_recall("h1")
        row = store.conn.execute(
            "SELECT recall_count, arousal FROM memories WHERE content_hash = 'h1'"
        ).fetchone()
        assert row["recall_count"] == 3
        assert row["arousal"] == pytest.approx(0.8)

    def test_nonexistent_hash(self, store):
        store.reinforce_recall("nonexistent")  # should not raise


class TestSearchResultHash:
    def test_search_result_has_content_hash(self):
        """SearchResult accepts content_hash field."""
        r = SearchResult(
            score=0.9, date="2026-03-26", content="test",
            arousal=0.5, source="semantic", content_hash="abc123",
        )
        assert r.content_hash == "abc123"

    def test_search_result_hash_default_none(self):
        """content_hash defaults to None."""
        r = SearchResult(
            score=0.9, date="2026-03-26", content="test",
            arousal=0.5, source="grep",
        )
        assert r.content_hash is None


class TestSemanticSearchHash:
    def test_semantic_returns_content_hash(self, store):
        """semantic_search includes content_hash from DB."""
        content = "### [INSIGHT] テスト洞察"
        ch = hashlib.sha256(content.encode()).hexdigest()
        vec = [0.1] * 384
        store.conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector) "
            "VALUES (?, ?, ?, ?, ?)",
            (ch, "2026-03-26", content, 0.8, json.dumps(vec)),
        )
        store.conn.commit()

        from cognitive_memory.search import semantic_search
        from cognitive_memory.scoring import normalize

        query_vec = normalize([0.1] * 384)
        results, status = semantic_search(
            query_vec, store.config.database_path, store.config, top_k=5
        )
        assert status == "ok"
        assert len(results) >= 1
        assert results[0].content_hash == ch
