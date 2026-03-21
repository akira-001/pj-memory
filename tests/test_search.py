"""Tests for search module: semantic+grep+merge, failOpen."""

import json
import sqlite3
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.scoring import normalize
from cognitive_memory.search import grep_search, merge_and_dedup, semantic_search
from cognitive_memory.types import SearchResult


@pytest.fixture
def indexed_db(tmp_path, mock_embedder):
    """Create a pre-populated SQLite DB for search tests."""
    db_path = tmp_path / "vectors.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE memories (
            id INTEGER PRIMARY KEY,
            content_hash TEXT UNIQUE,
            date TEXT,
            content TEXT,
            arousal REAL,
            vector BLOB
        )
    """)

    entries = [
        ("2026-03-21", "### [INSIGHT][TECH] 競合分析の結果\n*Arousal: 0.8*\nMem0とZepの比較分析完了", 0.8),
        ("2026-03-20", "### [DECISION][TECH] 検索パイプライン設計決定\n*Arousal: 0.6*\n3段階制約", 0.6),
        ("2026-03-15", "### [MILESTONE] ビジネスモデル策定完了\n*Arousal: 0.7*\nLTV:CAC 26:1", 0.7),
    ]

    import hashlib
    for date, content, arousal in entries:
        vec = mock_embedder.embed(content)
        h = hashlib.sha256(content.encode()).hexdigest()
        conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, vector) VALUES (?, ?, ?, ?, ?)",
            (h, date, content, arousal, json.dumps(vec)),
        )
    conn.commit()
    conn.close()
    return db_path


class TestSemanticSearch:
    def test_returns_results(self, indexed_db, mock_embedder):
        config = CogMemConfig()
        query_vec = mock_embedder.embed("競合分析")
        results, status = semantic_search(query_vec, indexed_db, config, top_k=5)
        assert status == "ok"
        assert len(results) == 3

    def test_results_sorted_by_score(self, indexed_db, mock_embedder):
        config = CogMemConfig()
        query_vec = mock_embedder.embed("test query")
        results, status = semantic_search(query_vec, indexed_db, config)
        assert status == "ok"
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_no_index_returns_empty(self, tmp_path, mock_embedder):
        config = CogMemConfig()
        query_vec = mock_embedder.embed("test")
        results, status = semantic_search(
            query_vec, tmp_path / "nonexistent.db", config
        )
        assert status == "no_index"
        assert results == []

    def test_top_k_limit(self, indexed_db, mock_embedder):
        config = CogMemConfig()
        query_vec = mock_embedder.embed("test")
        results, status = semantic_search(query_vec, indexed_db, config, top_k=1)
        assert len(results) == 1


class TestGrepSearch:
    def test_finds_keyword_matches(self, sample_log_file):
        config = CogMemConfig()
        results = grep_search("テスト 洞察", sample_log_file.parent, config)
        assert len(results) > 0
        assert all(r.source == "grep" for r in results)

    def test_no_keywords_returns_empty(self, sample_log_file):
        config = CogMemConfig()
        results = grep_search("", sample_log_file.parent, config)
        assert results == []

    def test_no_match_returns_empty(self, sample_log_file):
        config = CogMemConfig()
        results = grep_search("xyznotfound", sample_log_file.parent, config)
        assert results == []


class TestMergeDedup:
    def test_dedup_by_content_prefix(self):
        content = "Same content here that is long enough for dedup testing purposes"
        grep = [SearchResult(score=0.3, content=content, date="2026-03-21", arousal=0.5, source="grep")]
        semantic = [SearchResult(score=0.8, content=content, date="2026-03-21", arousal=0.5, source="semantic")]
        merged = merge_and_dedup(grep, semantic, top_k=5)
        assert len(merged) == 1
        assert merged[0].source == "semantic"  # semantic has priority

    def test_sorted_by_score(self):
        grep = [SearchResult(score=0.9, content="grep result high score", date="2026-03-21", arousal=0.8, source="grep")]
        semantic = [SearchResult(score=0.5, content="semantic result lower", date="2026-03-21", arousal=0.3, source="semantic")]
        merged = merge_and_dedup(grep, semantic, top_k=5)
        assert merged[0].score > merged[1].score

    def test_top_k_limit(self):
        results = [
            SearchResult(score=0.1 * i, content=f"entry {i} with unique content", date="2026-01-01", arousal=0.5, source="grep")
            for i in range(10)
        ]
        merged = merge_and_dedup(results, [], top_k=3)
        assert len(merged) == 3
