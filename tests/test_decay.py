"""Tests for memory decay logic — human-like forgetting mechanism."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cognitive_memory.decay import DecayAction, evaluate_entry


class TestEvaluateEntry:
    """Test evaluate_entry() decision logic."""

    # --- Rule 1: High arousal → KEEP ---

    def test_high_arousal_keeps(self):
        """High arousal (>= 0.7) memories persist regardless of recall."""
        result = evaluate_entry(arousal=0.9, recall_count=0, last_recalled=None)
        assert result == DecayAction.KEEP

    def test_arousal_at_threshold_keeps(self):
        """Arousal exactly at threshold (0.7) → KEEP."""
        result = evaluate_entry(arousal=0.7, recall_count=0, last_recalled=None)
        assert result == DecayAction.KEEP

    def test_arousal_just_below_threshold_not_keep(self):
        """Arousal just below threshold (0.69) → should NOT be KEEP."""
        result = evaluate_entry(arousal=0.69, recall_count=0, last_recalled=None)
        assert result != DecayAction.KEEP

    # --- Rule 2: Frequently recalled + recent → KEEP ---

    def test_frequent_recent_recall_keeps(self):
        """recall_count >= 2 with recent recall → KEEP."""
        recent = (datetime.now() - timedelta(days=30)).isoformat()
        result = evaluate_entry(arousal=0.5, recall_count=3, last_recalled=recent)
        assert result == DecayAction.KEEP

    def test_recall_at_threshold_recent_keeps(self):
        """recall_count exactly at threshold (2) with recent recall → KEEP."""
        recent = (datetime.now() - timedelta(days=1)).isoformat()
        result = evaluate_entry(arousal=0.4, recall_count=2, last_recalled=recent)
        assert result == DecayAction.KEEP

    # --- Rule 3: Frequently recalled + stale → DELETE ---

    def test_frequent_stale_recall_deletes(self):
        """recall_count >= 2 but last recalled > 18 months ago → DELETE."""
        stale = (datetime.now() - timedelta(days=600)).isoformat()
        result = evaluate_entry(arousal=0.5, recall_count=5, last_recalled=stale)
        assert result == DecayAction.DELETE

    def test_frequent_recall_none_last_recalled_deletes(self):
        """recall_count >= 2 but last_recalled=None → DELETE."""
        result = evaluate_entry(arousal=0.5, recall_count=3, last_recalled=None)
        assert result == DecayAction.DELETE

    # --- Rule 4: Low arousal + low recall → COMPACT ---

    def test_low_arousal_low_recall_compacts(self):
        """Low arousal + low recall count → COMPACT."""
        result = evaluate_entry(arousal=0.4, recall_count=0, last_recalled=None)
        assert result == DecayAction.COMPACT

    def test_recall_count_one_compacts(self):
        """recall_count=1 (below threshold of 2) → COMPACT."""
        recent = datetime.now().isoformat()
        result = evaluate_entry(arousal=0.5, recall_count=1, last_recalled=recent)
        assert result == DecayAction.COMPACT

    # --- Custom thresholds ---

    def test_custom_arousal_threshold(self):
        """Custom arousal_threshold changes the boundary."""
        # 0.5 is below default 0.7 but above custom 0.4
        result = evaluate_entry(
            arousal=0.5,
            recall_count=0,
            last_recalled=None,
            arousal_threshold=0.4,
        )
        assert result == DecayAction.KEEP

    def test_custom_recall_threshold(self):
        """Custom recall_threshold changes the boundary."""
        recent = datetime.now().isoformat()
        # recall_count=1 is below default 2 but meets custom 1
        result = evaluate_entry(
            arousal=0.4,
            recall_count=1,
            last_recalled=recent,
            recall_threshold=1,
        )
        assert result == DecayAction.KEEP

    def test_custom_recall_window(self):
        """Custom recall_window_months changes the staleness boundary."""
        # 400 days ago: within default 18 months (540 days), but outside 6 months (180 days)
        borderline = (datetime.now() - timedelta(days=400)).isoformat()
        result = evaluate_entry(
            arousal=0.4,
            recall_count=2,
            last_recalled=borderline,
            recall_window_months=6,
        )
        assert result == DecayAction.DELETE


class TestDecayAction:
    """Test DecayAction enum values."""

    def test_enum_values(self):
        assert DecayAction.KEEP.value == "keep"
        assert DecayAction.COMPACT.value == "compact"
        assert DecayAction.DELETE.value == "delete"


# --- Integration tests for apply_decay() ---

import hashlib
import sqlite3
import tempfile
from pathlib import Path

from cognitive_memory.config import CogMemConfig
from cognitive_memory.decay import apply_decay

# Helper: sample log with low arousal entries (all should compact)
LOW_AROUSAL_LOG = """\
# 2026-01-10 セッションログ

## セッション概要
テスト用のログ

## ログエントリ

### [DECISION] テスト設定の変更
*Arousal: 0.4 | Emotion: Neutral*
テスト設定を変更した。特に重要なものではない。

---

### [MILESTONE] ドキュメント整理完了
*Arousal: 0.5 | Emotion: Completion*
ドキュメントの整理が完了した。日常的な作業。

---

## 引き継ぎ
- **継続テーマ**: なし
"""

# Helper: log with one high arousal entry (should keep detail)
HIGH_AROUSAL_LOG = """\
# 2026-01-15 セッションログ

## セッション概要
重要な発見があったセッション

## ログエントリ

### [INSIGHT] 重大な気づき
*Arousal: 0.9 | Emotion: Surprise*
これは非常に重要な発見で、プロジェクトの方向性を変えた。
前提が完全に間違っていたことが判明した。

---

### [DECISION] 軽微な決定
*Arousal: 0.4 | Emotion: Neutral*
ログの書式を少し変えた。

---

## 引き継ぎ
- **継続テーマ**: 発見の検証
"""


def _make_config(tmp_path: Path, last_checkpoint: str = "2026-03-01") -> CogMemConfig:
    """Create a minimal config for testing."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "vectors.db"
    return CogMemConfig(
        logs_dir=str(logs_dir),
        db_path=str(db_path),
        last_checkpoint=last_checkpoint,
        _base_dir=str(tmp_path),
    )


def _init_db(db_path: Path):
    """Create the memories table in a fresh DB."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id           INTEGER PRIMARY KEY,
            content_hash TEXT UNIQUE,
            date         TEXT,
            content      TEXT,
            arousal      REAL,
            vector       BLOB,
            recall_count INTEGER DEFAULT 0,
            last_recalled TEXT
        )
    """
    )
    conn.commit()
    return conn


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class TestApplyDecay:
    """Integration tests for apply_decay()."""

    def test_all_low_arousal_creates_compact(self, tmp_path):
        """Consolidated log with all low-arousal entries → compact created, detail deleted."""
        config = _make_config(tmp_path, last_checkpoint="2026-03-01")
        log_file = config.logs_path / "2026-01-10.md"
        log_file.write_text(LOW_AROUSAL_LOG, encoding="utf-8")

        # Set up DB with no recall data (defaults: recall_count=0, last_recalled=None)
        conn = _init_db(config.database_path)
        conn.close()

        result = apply_decay(config, dry_run=False)

        assert result["compacted"] >= 1
        assert result["kept"] == 0
        # Detail file should be deleted
        assert not log_file.exists()
        # Compact file should exist
        compact_file = config.logs_path / "2026-01-10.compact.md"
        assert compact_file.exists()
        content = compact_file.read_text(encoding="utf-8")
        assert "[DECISION]" in content
        assert "[MILESTONE]" in content

    def test_high_arousal_preserves_detail(self, tmp_path):
        """Log with high-arousal entry → detail preserved (not compacted)."""
        config = _make_config(tmp_path, last_checkpoint="2026-03-01")
        log_file = config.logs_path / "2026-01-15.md"
        log_file.write_text(HIGH_AROUSAL_LOG, encoding="utf-8")

        conn = _init_db(config.database_path)
        conn.close()

        result = apply_decay(config, dry_run=False)

        assert result["kept"] >= 1
        # Detail file should still exist
        assert log_file.exists()

    def test_dry_run_no_modifications(self, tmp_path):
        """dry_run=True → no files modified."""
        config = _make_config(tmp_path, last_checkpoint="2026-03-01")
        log_file = config.logs_path / "2026-01-10.md"
        log_file.write_text(LOW_AROUSAL_LOG, encoding="utf-8")

        conn = _init_db(config.database_path)
        conn.close()

        result = apply_decay(config, dry_run=True)

        assert result["compacted"] >= 1
        # Files should NOT be modified
        assert log_file.exists()
        compact_file = config.logs_path / "2026-01-10.compact.md"
        assert not compact_file.exists()

    def test_recent_log_skipped(self, tmp_path):
        """Log newer than last_checkpoint → skipped (unconsolidated)."""
        config = _make_config(tmp_path, last_checkpoint="2026-01-01")
        # This log date (2026-01-15) is AFTER last_checkpoint (2026-01-01)
        log_file = config.logs_path / "2026-01-15.md"
        log_file.write_text(LOW_AROUSAL_LOG, encoding="utf-8")

        conn = _init_db(config.database_path)
        conn.close()

        result = apply_decay(config, dry_run=False)

        assert result["skipped"] >= 1
        # File should still exist — not processed
        assert log_file.exists()

    def test_existing_compact_deletes_detail(self, tmp_path):
        """Log that already has .compact.md → detail deleted."""
        config = _make_config(tmp_path, last_checkpoint="2026-03-01")
        log_file = config.logs_path / "2026-01-10.md"
        log_file.write_text(LOW_AROUSAL_LOG, encoding="utf-8")
        compact_file = config.logs_path / "2026-01-10.compact.md"
        compact_file.write_text("# existing compact\n- [DECISION] old entry\n", encoding="utf-8")

        conn = _init_db(config.database_path)
        conn.close()

        result = apply_decay(config, dry_run=False)

        # Detail file should be deleted
        assert not log_file.exists()
        # Compact file should still exist (either original or regenerated)
        assert compact_file.exists()

    def test_recall_count_from_db(self, tmp_path):
        """Entries with high recall_count + recent last_recalled → KEEP."""
        config = _make_config(tmp_path, last_checkpoint="2026-03-01")
        log_file = config.logs_path / "2026-01-10.md"
        log_file.write_text(LOW_AROUSAL_LOG, encoding="utf-8")

        conn = _init_db(config.database_path)
        # Insert a memory with high recall count for one of the entries
        entry_text = "### [DECISION] テスト設定の変更\n*Arousal: 0.4 | Emotion: Neutral*\nテスト設定を変更した。特に重要なものではない。"
        ch = _content_hash(entry_text)
        recent = (datetime.now() - timedelta(days=5)).isoformat()
        conn.execute(
            "INSERT INTO memories (content_hash, date, content, arousal, recall_count, last_recalled) VALUES (?, ?, ?, ?, ?, ?)",
            (ch, "2026-01-10", entry_text, 0.4, 5, recent),
        )
        conn.commit()
        conn.close()

        result = apply_decay(config, dry_run=False)

        # At least one entry has KEEP (from DB recall data), so detail is preserved
        assert result["kept"] >= 1
        assert log_file.exists()

    def test_empty_last_checkpoint_skips_all(self, tmp_path):
        """Empty last_checkpoint → all files skipped (no consolidation done yet)."""
        config = _make_config(tmp_path, last_checkpoint="")
        log_file = config.logs_path / "2026-01-10.md"
        log_file.write_text(LOW_AROUSAL_LOG, encoding="utf-8")

        conn = _init_db(config.database_path)
        conn.close()

        result = apply_decay(config, dry_run=False)

        assert result["skipped"] >= 1
        assert log_file.exists()
