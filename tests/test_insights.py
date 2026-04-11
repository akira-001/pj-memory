"""Tests for InsightsEngine."""
import sqlite3
from datetime import datetime, timedelta

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.insights import InsightsEngine


@pytest.fixture
def db_with_memories(tmp_path):
    db_path = tmp_path / "vectors.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE memories (
            id INTEGER PRIMARY KEY,
            content_hash TEXT UNIQUE,
            date TEXT,
            content TEXT,
            arousal REAL,
            vector BLOB,
            recall_count INTEGER DEFAULT 0,
            last_recalled TEXT
        )
    """)
    today = datetime.now().date().isoformat()
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
    entries = [
        ("h1", today, "### [INSIGHT] Important decision\n*Arousal: 0.9*\nContent.", 0.9, 3, today),
        ("h2", today, "### [DECISION] Chose approach A\n*Arousal: 0.7*\nContent.", 0.7, 1, None),
        ("h3", yesterday, "### [ERROR] Bug found\n*Arousal: 0.8*\nContent.", 0.8, 0, None),
        ("h4", yesterday, "### [PATTERN] Deploy pattern\n*Arousal: 0.5*\nContent.", 0.5, 2, yesterday),
    ]
    for h, date_, content, arousal, recall_count, last_recalled in entries:
        conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector, recall_count, last_recalled) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (h, date_, content, arousal, "[]", recall_count, last_recalled),
        )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def engine(db_with_memories):
    cfg = CogMemConfig(db_path=str(db_with_memories), _base_dir="")
    return InsightsEngine(cfg)


class TestInsightsEngine:
    def test_generate_returns_dict(self, engine):
        assert isinstance(engine.generate(), dict)

    def test_total_memories(self, engine):
        assert engine.generate()["total_memories"] == 4

    def test_avg_arousal_in_range(self, engine):
        avg = engine.generate()["avg_arousal"]
        assert 0.0 <= avg <= 1.0

    def test_arousal_buckets_structure(self, engine):
        buckets = engine.generate()["arousal_buckets"]
        assert isinstance(buckets, list)
        assert len(buckets) == 4
        for b in buckets:
            assert "label" in b
            assert "count" in b

    def test_top_recalled_sorted(self, engine):
        top = engine.generate()["top_recalled"]
        assert isinstance(top, list)
        if len(top) >= 2:
            assert top[0]["recall_count"] >= top[1]["recall_count"]

    def test_category_counts(self, engine):
        counts = engine.generate()["category_counts"]
        assert counts.get("INSIGHT", 0) >= 1
        assert counts.get("DECISION", 0) >= 1
        assert counts.get("ERROR", 0) >= 1

    def test_daily_counts(self, engine):
        daily = engine.generate()["daily_counts"]
        assert isinstance(daily, list)
        assert len(daily) >= 1

    def test_empty_db(self, tmp_path):
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY, content_hash TEXT, date TEXT, content TEXT, arousal REAL, vector BLOB, recall_count INTEGER DEFAULT 0, last_recalled TEXT)")
        conn.commit()
        conn.close()
        engine = InsightsEngine(CogMemConfig(db_path=str(db_path), _base_dir=""))
        report = engine.generate()
        assert report["total_memories"] == 0
        assert report["empty"] is True

    def test_days_filter(self, engine):
        report_all = engine.generate(days=None)
        report_1day = engine.generate(days=1)
        # 1-day lookback should have <= total memories
        assert report_1day["total_memories"] <= report_all["total_memories"]
