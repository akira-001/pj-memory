"""Tests for déjà vu search — finding entries by prior names / aliases."""

from __future__ import annotations

import subprocess

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.store import MemoryStore

requires_ollama = pytest.mark.skipif(
    subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/tags"],
        capture_output=True, timeout=3,
    ).returncode != 0,
    reason="Ollama not running",
)


VIVID_MILESTONE = """\
# 2026-03-26 セッションログ

## セッション概要

## ログエントリ

### [MILESTONE] ダッシュボード「記憶の定着」ページ実装
*Arousal: 0.8 | Emotion: Achievement*
元々「結晶化（Crystallization）」と呼んでいた機能のダッシュボードページ。
Akira が「結晶化という名前がピンとこない」と言ったのがきっかけで
同日に用語変更を決定し、コード側は最初から「記憶の定着」で統一した。
TDD で21テスト、シグナル表・チェックポイント・エラーパターン一覧を表示。

---

## 引き継ぎ
"""

# 比較用: 鮮明でない記録（旧名なし）
FLAT_MILESTONE = """\
# 2026-03-26 セッションログ

## セッション概要

## ログエントリ

### [MILESTONE] ダッシュボード「記憶の定着」ページ実装
*Arousal: 0.7 | Emotion: Achievement*
TDD で21テスト。シグナル表・チェックポイント・エラーパターン一覧を表示。

---

## 引き継ぎ
"""


@requires_ollama
class TestDejaVuSearch:
    """Vivid entries with prior names are discoverable by old terminology."""

    def _build_store(self, tmp_path, log_content):
        logs_dir = tmp_path / "memory" / "logs"
        logs_dir.mkdir(parents=True)
        log_file = logs_dir / "2026-03-26.md"
        log_file.write_text(log_content, encoding="utf-8")
        (tmp_path / "cogmem.toml").write_text(
            '[cogmem]\nlogs_dir = "memory/logs"\ndb_path = "memory/vectors.db"\n',
            encoding="utf-8",
        )
        config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
        store = MemoryStore(config)
        store.index_file(log_file, force=True)
        return store

    def test_vivid_entry_found_by_old_name(self, tmp_path):
        """Searching '結晶化のページ' finds the vivid entry with prior name."""
        store = self._build_store(tmp_path, VIVID_MILESTONE)
        response = store.search("結晶化のページ", top_k=3)
        results = response.results
        assert len(results) >= 1
        top = results[0]
        assert "記憶の定着" in top.content
        # デジャヴ発動閾値は 0.80 だが、ここではエントリが発見可能かを検証
        # 閾値以下でもヒットすること自体は正しい（プロトコル側でフィルタする）
        assert top.score >= 0.70

    def test_flat_entry_less_discoverable(self, tmp_path):
        """Flat entry without prior name scores lower for old terminology."""
        flat_path = tmp_path / "flat"
        vivid_path = tmp_path / "vivid"
        flat_store = self._build_store(flat_path, FLAT_MILESTONE)
        vivid_store = self._build_store(vivid_path, VIVID_MILESTONE)
        flat_results = flat_store.search("結晶化のページ", top_k=3).results
        vivid_results = vivid_store.search("結晶化のページ", top_k=3).results
        if flat_results and vivid_results:
            assert vivid_results[0].score >= flat_results[0].score

    def test_current_name_still_works(self, tmp_path):
        """Searching by current name also finds vivid entry."""
        store = self._build_store(tmp_path, VIVID_MILESTONE)
        response = store.search("記憶の定着ページ", top_k=3)
        results = response.results
        assert len(results) >= 1
        assert results[0].score >= 0.70
