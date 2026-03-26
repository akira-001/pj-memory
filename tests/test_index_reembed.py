"""Tests for re-indexing with content changes (stale entry cleanup)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.store import MemoryStore


LOG_V1 = """\
# 2026-03-26 セッションログ

## セッション概要

## ログエントリ

### [MILESTONE] Feature X 実装完了
*Arousal: 0.7 | Emotion: Achievement*
Feature X を実装した。

---

### [DECISION] ライブラリ Y を採用
*Arousal: 0.5 | Emotion: Pragmatism*
ライブラリ Y を選択した。

---

## 引き継ぎ
"""

# V2: MILESTONE entry rewritten with vivid format, DECISION unchanged
LOG_V2 = """\
# 2026-03-26 セッションログ

## セッション概要

## ログエントリ

### [MILESTONE] Feature X 実装完了
*Arousal: 0.8 | Emotion: Achievement*
当初は Feature Z（旧名）と呼んでいた機能。
Akira が「X のほうがわかりやすい」と言ったのがきっかけでリネーム。
TDD で15テスト、全パス。3日かけて完成。

---

### [DECISION] ライブラリ Y を採用
*Arousal: 0.5 | Emotion: Pragmatism*
ライブラリ Y を選択した。

---

## 引き継ぎ
"""


@pytest.fixture
def store_with_v1(tmp_path):
    """Store with V1 log indexed."""
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)
    log_file = logs_dir / "2026-03-26.md"
    log_file.write_text(LOG_V1, encoding="utf-8")
    (tmp_path / "cogmem.toml").write_text(
        '[cogmem]\nlogs_dir = "memory/logs"\ndb_path = "memory/vectors.db"\n',
        encoding="utf-8",
    )
    config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
    store = MemoryStore(config)

    # Use dummy embedder to avoid Ollama dependency
    class DummyEmbedder:
        def embed(self, text):
            return [0.1] * 384
        def embed_batch(self, texts):
            return [[0.1 + i * 0.001] * 384 for i in range(len(texts))]
    store._embedder = DummyEmbedder()

    store.index_file(log_file, force=True)
    return store, log_file, config


class TestReindexWithContentChanges:
    """When log content is edited, stale entries are cleaned up on re-index."""

    def test_v1_indexed_correctly(self, store_with_v1):
        """Baseline: V1 has 2 entries."""
        store, _, _ = store_with_v1
        rows = store.conn.execute(
            "SELECT COUNT(*) as n FROM memories WHERE date = '2026-03-26'"
        ).fetchone()
        assert rows["n"] == 2

    def test_reindex_removes_stale_entries(self, store_with_v1):
        """After editing and re-indexing, old MILESTONE is replaced, DECISION kept."""
        store, log_file, _ = store_with_v1

        # Overwrite with V2
        log_file.write_text(LOG_V2, encoding="utf-8")
        store.index_file(log_file, force=True)

        rows = store.conn.execute(
            "SELECT content FROM memories WHERE date = '2026-03-26'"
        ).fetchall()
        contents = [r["content"] for r in rows]

        # Should have exactly 2 entries (not 3)
        assert len(contents) == 2

        # New vivid MILESTONE should be present
        vivid_found = any("Feature Z（旧名）" in c for c in contents)
        assert vivid_found, "Vivid MILESTONE not found"

        # Old flat MILESTONE should be gone
        old_found = any("Feature X を実装した。" in c and "Feature Z" not in c for c in contents)
        assert not old_found, "Old flat MILESTONE still present"

        # Unchanged DECISION should still be there
        decision_found = any("ライブラリ Y を選択した" in c for c in contents)
        assert decision_found, "Unchanged DECISION was wrongly deleted"

    def test_reindex_preserves_recall_count(self, store_with_v1):
        """Unchanged entries keep their recall_count after re-index."""
        store, log_file, _ = store_with_v1

        # Simulate recall on the DECISION entry
        decision_hash = hashlib.sha256(
            "### [DECISION] ライブラリ Y を採用\n*Arousal: 0.5 | Emotion: Pragmatism*\nライブラリ Y を選択した。".encode()
        ).hexdigest()
        store.conn.execute(
            "UPDATE memories SET recall_count = 3 WHERE content_hash = ?",
            (decision_hash,),
        )
        store.conn.commit()

        # Re-index with V2
        log_file.write_text(LOG_V2, encoding="utf-8")
        store.index_file(log_file, force=True)

        # DECISION's recall_count should be preserved (same hash, INSERT OR IGNORE)
        row = store.conn.execute(
            "SELECT recall_count FROM memories WHERE content_hash = ?",
            (decision_hash,),
        ).fetchone()
        assert row is not None
        assert row["recall_count"] == 3

    def test_entry_count_correct_after_multiple_reindexes(self, store_with_v1):
        """Multiple re-indexes don't accumulate entries."""
        store, log_file, _ = store_with_v1

        # Re-index V1 again (no changes)
        store.index_file(log_file, force=True)
        rows = store.conn.execute(
            "SELECT COUNT(*) as n FROM memories WHERE date = '2026-03-26'"
        ).fetchone()
        assert rows["n"] == 2

        # Now change to V2
        log_file.write_text(LOG_V2, encoding="utf-8")
        store.index_file(log_file, force=True)
        rows = store.conn.execute(
            "SELECT COUNT(*) as n FROM memories WHERE date = '2026-03-26'"
        ).fetchone()
        assert rows["n"] == 2

        # Re-index V2 again (no changes)
        store.index_file(log_file, force=True)
        rows = store.conn.execute(
            "SELECT COUNT(*) as n FROM memories WHERE date = '2026-03-26'"
        ).fetchone()
        assert rows["n"] == 2
