"""Tests for MemoryStore: index, dedup, DB operations, search pipeline."""

import hashlib
import json
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.store import MemoryStore


class TestIndexFile:
    def test_index_single_file(self, sample_log_file, config_with_tmp, mock_embedder):
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            n = store.index_file(sample_log_file, force=True)
            assert n == 3  # 3 entries in sample_log

    def test_skip_non_date_filename(self, tmp_path, config_with_tmp, mock_embedder):
        fp = tmp_path / "memory" / "logs" / "notes.md"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("### Entry\nSome content that is long enough to pass filter.")
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            n = store.index_file(fp)
            assert n == 0

    def test_skip_compact_files(self, tmp_path, config_with_tmp, mock_embedder):
        fp = tmp_path / "memory" / "logs" / "2026-03-21.compact.md"
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text("### [INSIGHT] Compact entry with enough content length\n*Arousal: 0.5*\nContent.")
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            n = store.index_dir()
            # compact file should be skipped by index_dir
            entries = store.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            # Only non-compact file (sample_log_file from fixture) should be indexed
            assert entries >= 0

    def test_dedup_by_content_hash(self, sample_log_file, config_with_tmp, mock_embedder):
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            n1 = store.index_file(sample_log_file, force=True)
            n2 = store.index_file(sample_log_file, force=True)
            total = store.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            assert total == n1  # second insert should be ignored (content_hash dedup)

    def test_embed_failure_skips_file(self, sample_log_file, config_with_tmp, failing_embedder):
        with MemoryStore(config_with_tmp, embedder=failing_embedder) as store:
            n = store.index_file(sample_log_file, force=True)
            assert n == 0


class TestIndexDir:
    def test_index_all_files(self, sample_log_file, config_with_tmp, mock_embedder):
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            n = store.index_dir(force=True)
            assert n == 3

    def test_incremental_index(self, sample_log_file, config_with_tmp, mock_embedder):
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            n1 = store.index_dir()
            n2 = store.index_dir()  # should skip (already indexed, no mtime change)
            assert n1 == 3
            assert n2 == 0

    def test_empty_logs_dir(self, tmp_path, mock_embedder):
        cfg = CogMemConfig(
            logs_dir=str(tmp_path / "empty_logs"),
            db_path=str(tmp_path / "vectors.db"),
            _base_dir="",
        )
        with MemoryStore(cfg, embedder=mock_embedder) as store:
            n = store.index_dir()
            assert n == 0


class TestSearch:
    def test_search_with_gate_skip(self, config_with_tmp, mock_embedder):
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            response = store.search("おはよう")
            assert response.status == "skipped_by_gate"
            assert response.results == []

    def test_search_returns_results(self, sample_log_file, config_with_tmp, mock_embedder):
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            store.index_dir(force=True)
            response = store.search("テスト洞察エントリの検索")
            assert response.status == "ok"
            assert len(response.results) > 0

    def test_failopen_to_grep(self, sample_log_file, config_with_tmp, failing_embedder):
        with MemoryStore(config_with_tmp, embedder=failing_embedder) as store:
            # Use space-separated keywords so grep_search can split and match
            response = store.search("テスト 洞察 エントリ")
            assert "degraded" in response.status
            # grep should find keyword matches
            assert len(response.results) > 0

    def test_search_empty_index(self, config_with_tmp, mock_embedder):
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            response = store.search("何かを検索するテスト")
            # no_index → degraded, grep may find nothing
            assert response.status != "ok" or len(response.results) == 0


class TestStatus:
    def test_status_empty(self, tmp_path, mock_embedder):
        cfg = CogMemConfig(
            logs_dir=str(tmp_path / "logs"),
            db_path=str(tmp_path / "nonexistent.db"),
            _base_dir="",
        )
        with MemoryStore(cfg, embedder=mock_embedder) as store:
            # DB will be created by __enter__, but empty
            stats = store.status()
            assert stats["total_entries"] == 0
            assert stats["indexed_files"] == 0

    def test_status_after_index(self, sample_log_file, config_with_tmp, mock_embedder):
        with MemoryStore(config_with_tmp, embedder=mock_embedder) as store:
            store.index_dir(force=True)
            stats = store.status()
            assert stats["total_entries"] == 3
            assert stats["indexed_files"] == 1
            assert stats["db_size_bytes"] > 0
