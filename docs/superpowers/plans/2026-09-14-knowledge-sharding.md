# Knowledge Sharding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `memory/knowledge/` の本文層を分野別シャードに分割し、knowledge を `vectors.db` の索引対象に加える。

**Architecture:** 設定キーが指す先がファイルかディレクトリかで単一/シャードを分岐する（互換は `resolve_shards` 1 箇所に閉じる）。`memories` テーブルに `kind` / `source` を足し、ログと knowledge を別の stale 削除スコープに分ける。knowledge 行は時間減衰を掛けない。移行はエントリ埋め込みと分野シードの最近傍で分類する。

**Tech Stack:** Python 3.11+, SQLite, pytest, Ollama（埋め込みのみ。生成 API は使わない）

**Spec:** `docs/superpowers/specs/2026-09-14-knowledge-sharding-design.md`

---

## Phase 構成

| Phase | タスク | 解く問題 | 単独でリリース可能か |
|---|---|---|---|
| Phase 1 | Task 1–8 | P2（検索不能）, P4（重複チェック） | **可能。** 既存のフラットファイルのまま knowledge が検索対象になる。移行不要 |
| Phase 2 | Task 9–13 | P1（コンフリクト）, P3（圧縮）, P5（split-brain） | Phase 1 に依存 |

Phase 1 だけで 0.34.0 として出せる。Phase 2 は 0.35.0 に回してもよい。

## File Structure

| ファイル | 責務 |
|---|---|
| `src/cognitive_memory/knowledge.py` | **新規。** シャード解決・knowledge パーサ・採番・health。互換分岐をここだけに閉じる |
| `src/cognitive_memory/cli/migrate_knowledge_cmd.py` | **新規。** `cogmem migrate-knowledge` |
| `src/cognitive_memory/config.py` | knowledge 設定キー追加 |
| `src/cognitive_memory/store.py` | スキーマ拡張、`index_knowledge_file()`、stale 削除のスコープ分離 |
| `src/cognitive_memory/search.py` | knowledge 行の減衰除外、旧スキーマ耐性 |
| `src/cognitive_memory/types.py` | `SearchResult.kind` |
| `src/cognitive_memory/signals.py` | knowledge health 報告 |
| `src/cognitive_memory/templates/{,ja/}skills/crystallize/SKILL.md` | 追記先変更 + P5 修正 |

`parser.py` の `parse_entries`（ログ用、h3 + `Arousal:` 前提）は**変更しない**。knowledge は別パーサ。

## 実行前の確認

```bash
cd /Users/akira/workspace/ai-dev/cognitive-memory-lib
git status --porcelain          # クリーンであること
PYTHONPATH=src .venv/bin/pytest tests/ -q
```

`PYTHONPATH=src` は必須。付けないとインストール済みパッケージを参照してしまう（2026-04-11 のログに記録あり）。

---

# Phase 1 — knowledge を検索可能にする

## Task 1: config に knowledge キーを追加

**Files:**
- Modify: `src/cognitive_memory/config.py:36-40`（`_DEFAULTS`）, `:104-108`（dataclass フィールド）, `:325-339`（`from_toml` の `cls(...)`）, `:239-243` の直後（path property）
- Test: `tests/test_config.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_config.py` の末尾に追記:

```python
def test_knowledge_principles_default():
    config = CogMemConfig(_base_dir="/tmp/proj")
    assert config.knowledge_principles == "memory/knowledge/principles.md"
    assert config.knowledge_principles_path == Path("/tmp/proj/memory/knowledge/principles.md")


def test_knowledge_arousal_default():
    config = CogMemConfig(_base_dir="/tmp/proj")
    assert config.knowledge_arousal == 0.6


def test_shard_warn_kb_default():
    config = CogMemConfig(_base_dir="/tmp/proj")
    assert config.shard_warn_kb == 64


def test_knowledge_keys_from_toml(tmp_path):
    (tmp_path / "cogmem.toml").write_text(
        "[cogmem.knowledge]\n"
        'principles = "memory/knowledge/principles"\n'
        "arousal = 0.8\n"
        "shard_warn_kb = 32\n",
        encoding="utf-8",
    )
    config = CogMemConfig.from_toml(tmp_path / "cogmem.toml")
    assert config.knowledge_principles == "memory/knowledge/principles"
    assert config.knowledge_arousal == 0.8
    assert config.shard_warn_kb == 32
```

`tests/test_config.py` の先頭に `from pathlib import Path` が無ければ追加する。

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_config.py -k knowledge -v`
Expected: FAIL — `AttributeError: 'CogMemConfig' object has no attribute 'knowledge_principles'`

- [ ] **Step 3: 実装**

`_DEFAULTS`（`config.py:38` の直後）に追加:

```python
    "knowledge_principles": "memory/knowledge/principles.md",
    "knowledge_arousal": 0.6,
    "shard_warn_kb": 64,
```

dataclass フィールド（`config.py:106` の直後）に追加:

```python
    knowledge_principles: str = _DEFAULTS["knowledge_principles"]
    knowledge_arousal: float = _DEFAULTS["knowledge_arousal"]
    shard_warn_kb: int = _DEFAULTS["shard_warn_kb"]
```

path property（`knowledge_insights_path` の直後）に追加:

```python
    @property
    def knowledge_principles_path(self) -> Path:
        p = Path(self.knowledge_principles)
        if p.is_absolute():
            return p
        return Path(self._base_dir) / self.knowledge_principles
```

`from_toml` の `cls(...)`（`knowledge_insights=...` の直後）に追加:

```python
            knowledge_principles=knowledge.get(
                "principles", _DEFAULTS["knowledge_principles"]
            ),
            knowledge_arousal=knowledge.get(
                "arousal", _DEFAULTS["knowledge_arousal"]
            ),
            shard_warn_kb=knowledge.get(
                "shard_warn_kb", _DEFAULTS["shard_warn_kb"]
            ),
```

- [ ] **Step 4: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_config.py -k knowledge -v`
Expected: PASS（4 件）

- [ ] **Step 5: コミット**

```bash
git add src/cognitive_memory/config.py tests/test_config.py
git commit -m "feat(config): knowledge_principles / knowledge_arousal / shard_warn_kb を追加"
```

---

## Task 2: `resolve_shards` — ファイル/ディレクトリ互換分岐

**Files:**
- Create: `src/cognitive_memory/knowledge.py`
- Test: `tests/test_knowledge.py`（新規）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_knowledge.py`:

```python
"""Tests for knowledge shard resolution and parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.knowledge import resolve_shards


def _config(tmp_path: Path) -> CogMemConfig:
    return CogMemConfig(_base_dir=str(tmp_path))


def test_resolve_shards_legacy_file(tmp_path):
    """設定がファイルを指す場合、そのファイル 1 枚を返す（レガシーモード）。"""
    target = tmp_path / "memory" / "knowledge" / "insights.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Insights\n", encoding="utf-8")

    shards = resolve_shards(_config(tmp_path), "insights")

    assert shards == [target]


def test_resolve_shards_directory(tmp_path):
    """ディレクトリを指す場合、配下の *.md をソート順で返す。"""
    d = tmp_path / "memory" / "knowledge" / "insights"
    d.mkdir(parents=True)
    (d / "testing.md").write_text("x", encoding="utf-8")
    (d / "backend.md").write_text("x", encoding="utf-8")
    (d / "notes.txt").write_text("x", encoding="utf-8")

    config = _config(tmp_path)
    config.knowledge_insights = "memory/knowledge/insights"

    shards = resolve_shards(config, "insights")

    assert shards == [d / "backend.md", d / "testing.md"]


def test_resolve_shards_missing(tmp_path):
    """存在しなければ空リスト。例外は投げない。"""
    assert resolve_shards(_config(tmp_path), "insights") == []


def test_resolve_shards_unknown_kind(tmp_path):
    with pytest.raises(ValueError):
        resolve_shards(_config(tmp_path), "nonexistent-kind")
```

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cognitive_memory.knowledge'`

- [ ] **Step 3: 実装**

`src/cognitive_memory/knowledge.py`:

```python
"""Knowledge layer: shard resolution, parsing, numbering, health.

The knowledge body files (insights / error-patterns / principles) may be
either a single flat markdown file (legacy) or a directory of per-domain
shards. Every caller goes through :func:`resolve_shards` so that the
compatibility branch lives in exactly one place.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from .config import CogMemConfig

#: Supported knowledge kinds mapped to the config attribute holding their path.
KINDS = {
    "insights": "knowledge_insights_path",
    "error-patterns": "knowledge_error_patterns_path",
    "principles": "knowledge_principles_path",
}


def resolve_shards(config: CogMemConfig, kind: str) -> List[Path]:
    """Return the shard files for ``kind``.

    A configured path pointing at a file yields that single file (legacy
    flat mode); a directory yields its ``*.md`` children in sorted order.
    A missing path yields an empty list.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown knowledge kind: {kind!r} (expected one of {sorted(KINDS)})")

    path: Path = getattr(config, KINDS[kind])
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.glob("*.md") if p.is_file())
    return []
```

- [ ] **Step 4: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -v`
Expected: PASS（4 件）

- [ ] **Step 5: コミット**

```bash
git add src/cognitive_memory/knowledge.py tests/test_knowledge.py
git commit -m "feat(knowledge): resolve_shards でファイル/ディレクトリ互換を一箇所に閉じる"
```

---

## Task 3: `parse_knowledge_entries` — h2 形式パーサ

**Files:**
- Modify: `src/cognitive_memory/knowledge.py`
- Test: `tests/test_knowledge.py`
- Create: `tests/fixtures/knowledge_insights.md`

**背景:** knowledge は `## INS-005: タイトル` の h2 形式で、`*Arousal: 0.7*` 行を持たない。日付は本文の `- **発見**: 2026-05-08 (Session H)` にある。ログ用の `parse_entries` は h3 + Arousal 前提なので流用できない。

- [ ] **Step 1: fixture を作る**

`tests/fixtures/knowledge_insights.md`:

```markdown
# Insights

## INS-001: XBRL decimals 属性の意味
- **発見**: 2026-04-02 (Session A)
- **教訓**: decimals は丸め桁であって有効桁ではない。値の信頼区間を誤解しない

## INS-002: cache の TTL は cachedAt timestamp で必ず管理する
- **背景**: 日付を持たないエントリ。date は None になる
- **教訓**: read-cache と write-cache は別物

## INS-003: 短い
```

- [ ] **Step 2: 失敗するテストを書く**

`tests/test_knowledge.py` に追記:

```python
from cognitive_memory.knowledge import parse_knowledge_entries

FIXTURE = Path(__file__).parent / "fixtures" / "knowledge_insights.md"


def test_parse_knowledge_entries_splits_on_h2():
    entries = list(parse_knowledge_entries(FIXTURE.read_text(encoding="utf-8"), FIXTURE))
    # INS-003 は 20 文字未満なので is_noise で落ちる
    assert [e.category for e in entries] == ["INS", "INS"]
    assert entries[0].content.startswith("## INS-001:")
    assert "decimals は丸め桁" in entries[0].content


def test_parse_knowledge_entries_extracts_date():
    entries = list(parse_knowledge_entries(FIXTURE.read_text(encoding="utf-8"), FIXTURE))
    assert entries[0].date == "2026-04-02"


def test_parse_knowledge_entries_missing_date_is_empty_string():
    entries = list(parse_knowledge_entries(FIXTURE.read_text(encoding="utf-8"), FIXTURE))
    assert entries[1].date == ""


def test_parse_knowledge_entries_uses_configured_arousal():
    entries = list(
        parse_knowledge_entries(
            FIXTURE.read_text(encoding="utf-8"), FIXTURE, arousal=0.8
        )
    )
    assert all(e.arousal == 0.8 for e in entries)


def test_parse_knowledge_entries_error_patterns():
    text = "# エラーパターン\n\n## EP-007: Haiku で言語ドリフト\n- **発見**: 2026-05-01\n- 十分な長さの本文をここに書いておく\n"
    entries = list(parse_knowledge_entries(text, Path("error-patterns/general.md")))
    assert len(entries) == 1
    assert entries[0].category == "EP"


def test_parse_knowledge_entries_ignores_h1_preamble():
    text = "# Insights\n\nこの前書きはエントリではないので拾われない。十分な長さがある。\n"
    assert list(parse_knowledge_entries(text, Path("x.md"))) == []
```

- [ ] **Step 3: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -k parse -v`
Expected: FAIL — `ImportError: cannot import name 'parse_knowledge_entries'`

- [ ] **Step 4: 実装**

`knowledge.py` の import に追加:

```python
import re
from typing import Iterator, List

from .parser import is_noise
from .types import MemoryEntry
```

`knowledge.py` の末尾に追加:

```python
#: ``## INS-005: title`` / ``## EP-012: title`` の見出し。
_ENTRY_HEADING = re.compile(r"^## (INS|EP)-(\d+):", re.MULTILINE)

#: ``- **発見**: 2026-05-08 (Session H)`` から日付を拾う。
_DISCOVERED_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def parse_knowledge_entries(
    md_text: str,
    source: Path,
    arousal: float = 0.6,
) -> Iterator[MemoryEntry]:
    """Extract ``## INS-NNN:`` / ``## EP-NNN:`` entries from a shard.

    Unlike :func:`cognitive_memory.parser.parse_entries` (h3 headings with an
    ``Arousal:`` line), knowledge entries are h2 and carry no arousal. The
    date is taken from the first ``YYYY-MM-DD`` in the entry body and is
    informational only — knowledge rows are not time-decayed.
    """
    matches = list(_ENTRY_HEADING.finditer(md_text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        block = md_text[m.start() : end].strip()
        if is_noise(block):
            continue
        date_match = _DISCOVERED_DATE.search(block)
        yield MemoryEntry(
            date=date_match.group(1) if date_match else "",
            content=block,
            arousal=arousal,
            category=m.group(1),
        )
```

- [ ] **Step 5: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -v`
Expected: PASS（10 件）

- [ ] **Step 6: コミット**

```bash
git add src/cognitive_memory/knowledge.py tests/test_knowledge.py tests/fixtures/knowledge_insights.md
git commit -m "feat(knowledge): h2 形式の INS/EP パーサを追加（ログ用パーサは変更しない）"
```

---

## Task 4: `next_entry_number` — シャード横断採番

**Files:**
- Modify: `src/cognitive_memory/knowledge.py`
- Test: `tests/test_knowledge.py`

**背景:** レジストリファイルを置くと全 append がそれを触り、解こうとしているコンフリクトを再生産する。採番はシャード横断 grep で最大値を取る。

- [ ] **Step 1: 失敗するテストを書く**

```python
from cognitive_memory.knowledge import next_entry_number


def test_next_entry_number_across_shards(tmp_path):
    d = tmp_path / "memory" / "knowledge" / "insights"
    d.mkdir(parents=True)
    (d / "backend.md").write_text("## INS-003: a\n## INS-011: b\n", encoding="utf-8")
    (d / "testing.md").write_text("## INS-007: c\n", encoding="utf-8")

    config = _config(tmp_path)
    config.knowledge_insights = "memory/knowledge/insights"

    assert next_entry_number(config, "insights") == 12


def test_next_entry_number_empty_corpus_starts_at_one(tmp_path):
    assert next_entry_number(_config(tmp_path), "insights") == 1


def test_next_entry_number_legacy_flat_file(tmp_path):
    target = tmp_path / "memory" / "knowledge" / "insights.md"
    target.parent.mkdir(parents=True)
    target.write_text("## INS-042: x\n", encoding="utf-8")

    assert next_entry_number(_config(tmp_path), "insights") == 43
```

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -k next_entry -v`
Expected: FAIL — `ImportError: cannot import name 'next_entry_number'`

- [ ] **Step 3: 実装**

```python
def next_entry_number(config: CogMemConfig, kind: str) -> int:
    """Return the next free ``NNN`` for ``kind``, scanning every shard.

    Deliberately derived from the shards themselves rather than a registry
    file: a registry would be touched by every append, recreating the
    write contention that sharding exists to remove.
    """
    highest = 0
    for shard in resolve_shards(config, kind):
        try:
            text = shard.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in _ENTRY_HEADING.finditer(text):
            highest = max(highest, int(m.group(2)))
    return highest + 1
```

- [ ] **Step 4: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -k next_entry -v`
Expected: PASS（3 件）

- [ ] **Step 5: コミット**

```bash
git add src/cognitive_memory/knowledge.py tests/test_knowledge.py
git commit -m "feat(knowledge): シャード横断の採番（レジストリを置かない）"
```

---

## Task 5: `memories` に `kind` / `source` を追加

**Files:**
- Modify: `src/cognitive_memory/store.py:69-99`
- Test: `tests/test_store.py`

**背景:** 既存の `ALTER TABLE memories ADD COLUMN` 移行ループに乗せる。既存行は `kind='log'` で埋まる — 今日 knowledge は索引されていないので正しい。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_store.py` の末尾に追記:

```python
def test_schema_has_kind_and_source(config_with_tmp, mock_embedder):
    store = MemoryStore(config_with_tmp, embedder=mock_embedder)
    cols = {row[1] for row in store.conn.execute("PRAGMA table_info(memories)")}
    assert "kind" in cols
    assert "source" in cols
    store.close()


def test_existing_rows_default_to_log_kind(config_with_tmp, mock_embedder, sample_log_file):
    """旧 DB からの移行で、既存行が kind='log' に埋まること。"""
    store = MemoryStore(config_with_tmp, embedder=mock_embedder)
    store.index_file(sample_log_file)
    kinds = {row[0] for row in store.conn.execute("SELECT kind FROM memories")}
    assert kinds == {"log"}
    store.close()
```

`tests/test_store.py` の import に `MemoryStore` が無ければ `from cognitive_memory.store import MemoryStore` を追加する。

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_store.py -k "kind or source" -v`
Expected: FAIL — `assert 'kind' in cols`

- [ ] **Step 3: 実装**

`store.py` の `CREATE TABLE memories`（`store.py:69-78`）の `last_recalled TEXT` の後に列を追加:

```python
                recall_count INTEGER DEFAULT 0,
                last_recalled TEXT,
                kind         TEXT DEFAULT 'log',
                source       TEXT
```

移行ループ（`store.py:90-93`）に追加:

```python
        for col, col_def in [
            ("recall_count", "INTEGER DEFAULT 0"),
            ("last_recalled", "TEXT"),
            ("kind", "TEXT DEFAULT 'log'"),
            ("source", "TEXT"),
        ]:
```

- [ ] **Step 4: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_store.py -v`
Expected: PASS（既存テストも全て）

- [ ] **Step 5: コミット**

```bash
git add src/cognitive_memory/store.py tests/test_store.py
git commit -m "feat(store): memories に kind / source 列を追加（既存行は kind='log'）"
```

---

## Task 6: stale 削除を `kind` でスコープする（回帰テスト）

**Files:**
- Modify: `src/cognitive_memory/store.py`（`index_file` 内の stale 削除）
- Test: `tests/test_store.py`

**背景（重要）:** 現行の stale 削除は `DELETE FROM memories WHERE date = ?` と日付キー。knowledge エントリが同じ日付を持つと、**ログの再索引が knowledge 行を巻き込んで消す**。knowledge を索引する前にここを直す。

- [ ] **Step 1: 失敗する回帰テストを書く**

```python
def test_log_reindex_does_not_delete_knowledge_rows(
    config_with_tmp, mock_embedder, sample_log_file
):
    """回帰: 日付キーの stale 削除が同日付の knowledge 行を巻き込まないこと。

    sample_log_file は 2026-03-21。同じ日付を持つ knowledge 行を直接入れて
    から、ログ本文を書き換えて再索引する。現行コードでは knowledge 行が消える。
    """
    store = MemoryStore(config_with_tmp, embedder=mock_embedder)
    store.index_file(sample_log_file)

    store.conn.execute(
        "INSERT INTO memories (content_hash, date, content, arousal, vector, kind, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("knowledge-hash-1", "2026-03-21", "## INS-001: 巻き込まれてはいけない知識",
         0.6, "[0.5,0.5,0.5,0.5]", "knowledge", "knowledge/insights/backend.md"),
    )
    store.conn.commit()

    # ログを書き換えて再索引 → 旧エントリが stale になる
    sample_log_file.write_text(
        "# 2026-03-21 セッションログ\n\n"
        "### [INSIGHT][TECH] 差し替え後の唯一のエントリ\n"
        "*Arousal: 0.7*\n"
        "内容を完全に入れ替えたので、以前のエントリは stale になる。\n",
        encoding="utf-8",
    )
    store.index_file(sample_log_file, force=True)

    survived = store.conn.execute(
        "SELECT COUNT(*) FROM memories WHERE kind = 'knowledge'"
    ).fetchone()[0]
    assert survived == 1
    store.close()
```

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_store.py -k reindex_does_not_delete -v`
Expected: FAIL — `assert 0 == 1`（knowledge 行が消える）

- [ ] **Step 3: 実装**

`store.py` の `index_file` 内、stale 抽出の SELECT と DELETE を `kind='log'` に限定する。

変更前:

```python
        existing = self.conn.execute(
            "SELECT content_hash FROM memories WHERE date = ?", (date,)
        ).fetchall()
```

変更後:

```python
        existing = self.conn.execute(
            "SELECT content_hash FROM memories WHERE date = ? AND kind = 'log'",
            (date,),
        ).fetchall()
```

DELETE 側も同様に限定する。変更前:

```python
            self.conn.executemany(
                "DELETE FROM memories WHERE content_hash = ?",
                [(h,) for h in stale],
            )
```

変更後:

```python
            self.conn.executemany(
                "DELETE FROM memories WHERE content_hash = ? AND kind = 'log'",
                [(h,) for h in stale],
            )
```

- [ ] **Step 4: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_store.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/cognitive_memory/store.py tests/test_store.py
git commit -m "fix(store): stale 削除を kind='log' に限定（同日付の knowledge 行の巻き込みを防ぐ）"
```

---

## Task 7: `index_knowledge_file` — ファイル名日付を要求しない索引

**Files:**
- Modify: `src/cognitive_memory/store.py`
- Test: `tests/test_store.py`

**背景:** 既存の `index_file` は `re.match(r"(\d{4}-\d{2}-\d{2})", filename)` にマッチしないと `return 0` する。`backend.md` は索引されず黙って 0 件で終わる。また `indexed_files` の PK が basename なので `logs/backend.md` と `knowledge/insights/backend.md` が衝突する。

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_index_knowledge_file_stores_rows(config_with_tmp, mock_embedder, tmp_path):
    d = tmp_path / "memory" / "knowledge" / "insights"
    d.mkdir(parents=True)
    shard = d / "backend.md"
    shard.write_text(
        "# Insights\n\n"
        "## INS-001: Prisma の接続プールは worker 数に合わせる\n"
        "- **発見**: 2026-04-02\n"
        "- **教訓**: 既定値のままだと並列ジョブで枯渇する\n",
        encoding="utf-8",
    )

    store = MemoryStore(config_with_tmp, embedder=mock_embedder)
    stored = store.index_knowledge_file(shard, kind="insights")

    assert stored == 1
    row = store.conn.execute(
        "SELECT kind, source FROM memories WHERE kind = 'knowledge'"
    ).fetchone()
    assert row["kind"] == "knowledge"
    assert row["source"].endswith("insights/backend.md")
    store.close()


def test_indexed_files_key_avoids_basename_collision(
    config_with_tmp, mock_embedder, tmp_path, sample_log_file
):
    """logs/backend.md と knowledge/insights/backend.md が別レコードになること。"""
    logs_backend = sample_log_file.parent / "2026-03-22.md"
    logs_backend.write_text(
        "# 2026-03-22\n\n### [INSIGHT][TECH] ログ側のエントリ\n*Arousal: 0.5*\n"
        "十分な長さのログ本文をここに置いておく。\n",
        encoding="utf-8",
    )

    d = tmp_path / "memory" / "knowledge" / "insights"
    d.mkdir(parents=True)
    shard = d / "2026-03-22.md"
    shard.write_text(
        "## INS-050: 同じ basename を持つ knowledge シャード\n"
        "- **発見**: 2026-03-22\n- 十分な長さの本文を置く\n",
        encoding="utf-8",
    )

    store = MemoryStore(config_with_tmp, embedder=mock_embedder)
    store.index_file(logs_backend)
    store.index_knowledge_file(shard, kind="insights")

    keys = {row[0] for row in store.conn.execute("SELECT filename FROM indexed_files")}
    assert "2026-03-22.md" in keys
    assert any(k.startswith("knowledge:") for k in keys)
    store.close()


def test_index_knowledge_file_stale_cleanup_by_source(
    config_with_tmp, mock_embedder, tmp_path
):
    """シャードからエントリを消したら、その source の古い行が消えること。"""
    d = tmp_path / "memory" / "knowledge" / "insights"
    d.mkdir(parents=True)
    shard = d / "backend.md"
    shard.write_text(
        "## INS-001: 残すほうのエントリ本文を十分な長さで書く\n"
        "- **発見**: 2026-04-02\n\n"
        "## INS-002: 消すほうのエントリ本文を十分な長さで書く\n"
        "- **発見**: 2026-04-03\n",
        encoding="utf-8",
    )

    store = MemoryStore(config_with_tmp, embedder=mock_embedder)
    store.index_knowledge_file(shard, kind="insights")
    assert store.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 2

    shard.write_text(
        "## INS-001: 残すほうのエントリ本文を十分な長さで書く\n"
        "- **発見**: 2026-04-02\n",
        encoding="utf-8",
    )
    store.index_knowledge_file(shard, kind="insights", force=True)

    assert store.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 1
    store.close()
```

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_store.py -k knowledge -v`
Expected: FAIL — `AttributeError: 'MemoryStore' object has no attribute 'index_knowledge_file'`

- [ ] **Step 3: 実装**

`store.py` の import に追加:

```python
from .knowledge import parse_knowledge_entries
```

`index_file` の直後に追加:

```python
    def index_knowledge_file(
        self, filepath: Path, kind: str, force: bool = False
    ) -> int:
        """Index one knowledge shard. Returns number of entries stored.

        Unlike :meth:`index_file` this does not require a date in the
        filename, keys ``indexed_files`` by a ``knowledge:`` prefixed
        relative path (basenames collide with log files otherwise), and
        scopes stale cleanup by ``source`` rather than by date.
        """
        try:
            rel = filepath.resolve().relative_to(Path(self.config._base_dir).resolve())
        except (ValueError, OSError):
            rel = filepath
        source = str(rel)
        file_key = f"knowledge:{source}"

        if not force:
            row = self.conn.execute(
                "SELECT indexed_at FROM indexed_files WHERE filename = ?", (file_key,)
            ).fetchone()
            if row:
                indexed_at = datetime.fromisoformat(row["indexed_at"])
                file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if file_mtime <= indexed_at:
                    return 0

        md_text = filepath.read_text(encoding="utf-8")
        entries = list(
            parse_knowledge_entries(md_text, filepath, self.config.knowledge_arousal)
        )

        new_hashes = {hashlib.sha256(e.content.encode()).hexdigest() for e in entries}
        existing = self.conn.execute(
            "SELECT content_hash FROM memories WHERE source = ? AND kind = 'knowledge'",
            (source,),
        ).fetchall()
        stale = [r["content_hash"] for r in existing if r["content_hash"] not in new_hashes]
        if stale:
            self.conn.executemany(
                "DELETE FROM memories WHERE content_hash = ? AND kind = 'knowledge'",
                [(h,) for h in stale],
            )
            print(
                f"  [CLEANUP] {source}: removed {len(stale)} stale entr"
                f"{'y' if len(stale) == 1 else 'ies'}",
                file=sys.stderr,
            )

        if not entries:
            self.conn.execute(
                "INSERT OR REPLACE INTO indexed_files (filename, indexed_at, entry_count) VALUES (?, ?, ?)",
                (file_key, datetime.now().isoformat(), 0),
            )
            self.conn.commit()
            return 0

        vectors = self.embedder.embed_batch([e.content for e in entries])
        if vectors is None:
            print(f"  [SKIP] {source}: embed failed", file=sys.stderr)
            return 0

        stored = 0
        for entry, vec in zip(entries, vectors):
            content_hash = hashlib.sha256(entry.content.encode()).hexdigest()
            try:
                self.conn.execute(
                    "INSERT OR IGNORE INTO memories "
                    "(content_hash, date, content, arousal, vector, kind, source) "
                    "VALUES (?, ?, ?, ?, ?, 'knowledge', ?)",
                    (
                        content_hash,
                        entry.date,
                        entry.content,
                        entry.arousal,
                        json.dumps(normalize(vec)),
                        source,
                    ),
                )
                stored += 1
            except sqlite3.Error as e:
                print(f"  [ERROR] SQLite write failed: {e}", file=sys.stderr)

        self.conn.execute(
            "INSERT OR REPLACE INTO indexed_files (filename, indexed_at, entry_count) VALUES (?, ?, ?)",
            (file_key, datetime.now().isoformat(), stored),
        )
        self.conn.commit()
        return stored
```

- [ ] **Step 4: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_store.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/cognitive_memory/store.py tests/test_store.py
git commit -m "feat(store): index_knowledge_file を追加（日付非依存・source スコープの stale 削除）"
```

---

## Task 8: `index_dir` が knowledge も回す + 検索の減衰除外

**Files:**
- Modify: `src/cognitive_memory/store.py`（`index_dir`）, `src/cognitive_memory/search.py`（`semantic_search`）, `src/cognitive_memory/types.py`（`SearchResult`）
- Test: `tests/test_store.py`, `tests/test_search.py`

**背景（重要）:** `semantic_search` は `MemoryStore._init_db` を通らず独自に `sqlite3.connect` する。旧バージョンが作った DB には `kind` 列が無いので、素朴に `SELECT kind` すると `OperationalError: no such column` で落ちる。列の有無を `PRAGMA table_info` で見てから SELECT を組む。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_search.py` に追記:

```python
import json
import sqlite3

from cognitive_memory.search import semantic_search


def _make_db(tmp_path, rows, with_kind=True):
    """rows: list of (content_hash, date, content, arousal, kind)"""
    db = tmp_path / "v.db"
    conn = sqlite3.connect(str(db))
    extra = ", kind TEXT DEFAULT 'log', source TEXT" if with_kind else ""
    conn.execute(
        "CREATE TABLE memories (id INTEGER PRIMARY KEY, content_hash TEXT UNIQUE, "
        f"date TEXT, content TEXT, arousal REAL, vector BLOB{extra})"
    )
    vec = json.dumps([1.0, 0.0, 0.0, 0.0])
    for h, date, content, arousal, kind in rows:
        if with_kind:
            conn.execute(
                "INSERT INTO memories (content_hash, date, content, arousal, vector, kind) "
                "VALUES (?,?,?,?,?,?)",
                (h, date, content, arousal, vec, kind),
            )
        else:
            conn.execute(
                "INSERT INTO memories (content_hash, date, content, arousal, vector) "
                "VALUES (?,?,?,?,?)",
                (h, date, content, arousal, vec),
            )
    conn.commit()
    conn.close()
    return db


def test_knowledge_rows_are_not_time_decayed(tmp_path):
    """古い knowledge 行が、同じ内容の古いログ行より高いスコアになること。"""
    db = _make_db(
        tmp_path,
        [
            ("h1", "2020-01-01", "古い知識", 0.6, "knowledge"),
            ("h2", "2020-01-01", "古いログ", 0.6, "log"),
        ],
    )
    config = CogMemConfig(_base_dir="")
    results, status = semantic_search([1.0, 0.0, 0.0, 0.0], db, config, top_k=5)

    assert status == "ok"
    by_kind = {r.kind: r for r in results}
    assert by_kind["knowledge"].time_decay == 1.0
    assert by_kind["log"].time_decay < 1.0
    assert by_kind["knowledge"].score > by_kind["log"].score


def test_semantic_search_tolerates_old_schema_without_kind(tmp_path):
    """kind 列を持たない旧 DB でも落ちずに検索できること。"""
    db = _make_db(
        tmp_path, [("h1", "2026-01-01", "旧スキーマの行", 0.5, None)], with_kind=False
    )
    config = CogMemConfig(_base_dir="")
    results, status = semantic_search([1.0, 0.0, 0.0, 0.0], db, config, top_k=5)

    assert status == "ok"
    assert results[0].kind == "log"
```

`tests/test_search.py` に `from cognitive_memory.config import CogMemConfig` が無ければ追加する。

`tests/test_store.py` に追記:

```python
def test_index_dir_indexes_knowledge_shards(config_with_tmp, mock_embedder, tmp_path):
    d = tmp_path / "memory" / "knowledge" / "insights"
    d.mkdir(parents=True)
    (d / "backend.md").write_text(
        "## INS-001: index_dir から拾われるべきエントリ本文\n- **発見**: 2026-04-02\n",
        encoding="utf-8",
    )
    config_with_tmp.knowledge_insights = "memory/knowledge/insights"

    store = MemoryStore(config_with_tmp, embedder=mock_embedder)
    store.index_dir()

    count = store.conn.execute(
        "SELECT COUNT(*) FROM memories WHERE kind = 'knowledge'"
    ).fetchone()[0]
    assert count == 1
    store.close()


def test_index_dir_indexes_legacy_flat_file(config_with_tmp, mock_embedder, tmp_path):
    """レガシーモード: 設定がフラットファイルを指していても索引されること。

    config_with_tmp は knowledge_insights を既定のまま
    （memory/knowledge/insights.md）にしておく。
    """
    k = tmp_path / "memory" / "knowledge"
    k.mkdir(parents=True)
    (k / "insights.md").write_text(
        "# Insights\n\n"
        "## INS-001: フラット運用のまま索引されるべきエントリ本文\n"
        "- **発見**: 2026-04-02\n",
        encoding="utf-8",
    )

    store = MemoryStore(config_with_tmp, embedder=mock_embedder)
    store.index_dir()

    row = store.conn.execute(
        "SELECT source FROM memories WHERE kind = 'knowledge'"
    ).fetchone()
    assert row is not None
    assert row["source"].endswith("knowledge/insights.md")
    store.close()
```

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_search.py -k "decay or old_schema" tests/test_store.py -k index_dir_indexes -v`
Expected: FAIL — `AttributeError: 'SearchResult' object has no attribute 'kind'`

- [ ] **Step 3: `SearchResult.kind` を追加**

`types.py` の `SearchResult` に追加（`content_hash` の後）:

```python
    kind: str = "log"  # "log" | "knowledge"
```

- [ ] **Step 4: `semantic_search` を実装**

`search.py` の `semantic_search` 内、SELECT とループを差し替える:

```python
    # The DB may predate the kind/source columns (semantic_search connects
    # directly and does not run MemoryStore._init_db), so probe first.
    cols = {r[1] for r in conn.execute("PRAGMA table_info(memories)")}
    kind_expr = "kind" if "kind" in cols else "'log' AS kind"

    t0 = time.time()
    results: List[SearchResult] = []
    try:
        for row in conn.execute(
            f"SELECT content_hash, date, content, arousal, vector, {kind_expr} FROM memories"
        ):
            v = json.loads(row["vector"])
            sim = cosine_sim(query_vec, v)
            kind = row["kind"] or "log"
            if kind == "knowledge":
                # Crystallized knowledge does not rot; do not decay it.
                decay = 1.0
            else:
                decay = time_decay(
                    row["date"],
                    row["arousal"],
                    base_half_life=config.base_half_life,
                    floor=config.decay_floor,
                )
            score = (config.sim_weight * sim + config.arousal_weight * row["arousal"]) * decay
            results.append(
                SearchResult(
                    score=round(score, 4),
                    date=row["date"],
                    content=row["content"],
                    arousal=row["arousal"],
                    source="semantic",
                    cosine_sim=round(sim, 4),
                    time_decay=round(decay, 4),
                    content_hash=row["content_hash"],
                    kind=kind,
                )
            )
```

- [ ] **Step 5: `index_dir` に knowledge を足す**

`store.py` の `index_dir` の `return total` の直前に追加:

```python
        # Knowledge shards (insights / error-patterns / principles).
        for kind in KINDS:
            for shard in resolve_shards(self.config, kind):
                n = self.index_knowledge_file(shard, kind=kind, force=force)
                if n > 0:
                    print(f"  {shard.name} ({kind}): {n} entries", file=sys.stderr)
                total += n
```

`store.py` の import を更新:

```python
from .knowledge import KINDS, parse_knowledge_entries, resolve_shards
```

- [ ] **Step 6: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/ -q`
Expected: PASS（全件）

- [ ] **Step 7: コミット**

```bash
git add src/cognitive_memory/store.py src/cognitive_memory/search.py src/cognitive_memory/types.py tests/
git commit -m "feat(search): knowledge を索引対象にし、時間減衰を掛けない（旧スキーマ耐性つき）"
```

**ここまでで Phase 1 完了。** 既存のフラットな `insights.md` / `error-patterns.md` が移行なしで検索可能になる。

---

# Phase 2 — シャード化と移行

## Task 9: `check_knowledge_health`

**Files:**
- Modify: `src/cognitive_memory/knowledge.py`, `src/cognitive_memory/signals.py:34,52,100`
- Test: `tests/test_knowledge.py`, `tests/test_signals.py`

**背景:** 本文シャードには**上限を掛けない。警告のみ**。#1692 の構造では索引が溢れたら本文へ移すので、本文は受け止める側。ここに上限を置くと逃がし先が無くなる。

- [ ] **Step 1: 失敗するテストを書く**

```python
from cognitive_memory.knowledge import check_knowledge_health


def test_knowledge_health_warns_on_large_shard(tmp_path):
    d = tmp_path / "memory" / "knowledge" / "insights"
    d.mkdir(parents=True)
    (d / "backend.md").write_text("x" * 70_000, encoding="utf-8")
    (d / "testing.md").write_text("x" * 100, encoding="utf-8")

    config = _config(tmp_path)
    config.knowledge_insights = "memory/knowledge/insights"

    health = check_knowledge_health(config)

    assert any("backend.md" in w for w in health.warnings)
    assert not any("testing.md" in w for w in health.warnings)


def test_knowledge_health_warns_on_legacy_flat_file(tmp_path):
    target = tmp_path / "memory" / "knowledge" / "insights.md"
    target.parent.mkdir(parents=True)
    target.write_text("## INS-001: x\n", encoding="utf-8")

    health = check_knowledge_health(_config(tmp_path))

    assert any("migrate-knowledge" in w for w in health.warnings)


def test_knowledge_health_clean_when_sharded_and_small(tmp_path):
    d = tmp_path / "memory" / "knowledge" / "insights"
    d.mkdir(parents=True)
    (d / "backend.md").write_text("## INS-001: x\n", encoding="utf-8")

    config = _config(tmp_path)
    config.knowledge_insights = "memory/knowledge/insights"

    assert check_knowledge_health(config).warnings == []
```

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -k health -v`
Expected: FAIL — `ImportError: cannot import name 'check_knowledge_health'`

- [ ] **Step 3: 実装**

`knowledge.py` の import に `from dataclasses import dataclass, field` を追加し、末尾に:

```python
@dataclass
class KnowledgeHealth:
    """Per-shard size report for the knowledge body layer."""

    shards: dict = field(default_factory=dict)  # relative path -> size_kb
    warn_kb: int = 0
    legacy_kinds: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "shards": self.shards,
            "warn_kb": self.warn_kb,
            "legacy_kinds": self.legacy_kinds,
            "warnings": self.warnings,
        }


def check_knowledge_health(config: CogMemConfig) -> KnowledgeHealth:
    """Report per-shard sizes and legacy flat-file usage.

    Shards are warned about, never capped: in the #1692 structure the body
    layer is where an overflowing index escapes to, so it must absorb.
    """
    health = KnowledgeHealth(warn_kb=config.shard_warn_kb)

    for kind in KINDS:
        configured: Path = getattr(config, KINDS[kind])
        if configured.is_file():
            health.legacy_kinds.append(kind)
            health.warnings.append(
                f"{kind} is a single flat file ({configured.name}). "
                f"Run `cogmem migrate-knowledge --kind {kind}` to shard it."
            )
        for shard in resolve_shards(config, kind):
            try:
                size_kb = round(shard.stat().st_size / 1024, 1)
            except OSError:
                continue
            health.shards[f"{kind}/{shard.name}"] = size_kb
            if config.shard_warn_kb > 0 and size_kb > config.shard_warn_kb:
                health.warnings.append(
                    f"{kind}/{shard.name} is {size_kb}KB "
                    f"(> {config.shard_warn_kb}KB). Split the domain or move "
                    "stale entries out. Raising the threshold is not the fix."
                )

    return health
```

- [ ] **Step 4: signals に配線**

`signals.py` の import に追加:

```python
from .knowledge import check_knowledge_health
```

`signals.py:34` のデータクラスに追加:

```python
    knowledge_health: Optional[dict] = None
```

`signals.py:52` の直後に追加:

```python
        if self.knowledge_health is not None:
            result["knowledge_health"] = self.knowledge_health
```

`signals.py:100` の `summary_health=...` の隣に追加:

```python
        knowledge_health=check_knowledge_health(config).to_dict(),
```

- [ ] **Step 5: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py tests/test_signals.py -v`
Expected: PASS

- [ ] **Step 6: コミット**

```bash
git add src/cognitive_memory/knowledge.py src/cognitive_memory/signals.py tests/
git commit -m "feat(knowledge): シャード別 health を signals に配線（上限ではなく警告）"
```

---

## Task 10: 分類器 — 埋め込み最近傍

**Files:**
- Modify: `src/cognitive_memory/knowledge.py`
- Test: `tests/test_knowledge.py`

**背景:** 生成 LLM クライアントは既存コードに無い（`embeddings/ollama.py` は埋め込み専用）。新設せず、**既にある埋め込みで最近傍分類**する。各分野のシード文（`summary-{分野}.md` の本文、無ければ既存シャードの中身）を埋め込み、エントリとの cosine が最大の分野に割り当てる。閾値未満は `_unsorted`。

これは論文の compile フェーズに当たるが、**クラスタリングもラベル生成もしない** — 分野名は人間が書いた `summary-*.md` を再利用する。ラベルを生成しないので TatQA 型の潰れが起きない。

- [ ] **Step 1: 失敗するテストを書く**

```python
from cognitive_memory.knowledge import classify_entries


class _StubEmbedder:
    """語彙ベースの決定的スタブ。'db' を含めば軸0、'ui' を含めば軸1。"""

    def embed_batch(self, texts):
        out = []
        for t in texts:
            lower = t.lower()
            if "db" in lower:
                out.append([1.0, 0.0])
            elif "ui" in lower:
                out.append([0.0, 1.0])
            else:
                out.append([0.7071, 0.7071])
        return out


def test_classify_entries_assigns_nearest_domain():
    seeds = {"backend": "db prisma", "frontend": "ui next.js"}
    entries = ["## INS-001: db の接続プール", "## INS-002: ui の再描画"]

    assigned = classify_entries(entries, seeds, _StubEmbedder(), threshold=0.8)

    assert assigned == ["backend", "frontend"]


def test_classify_entries_below_threshold_goes_unsorted():
    seeds = {"backend": "db prisma", "frontend": "ui next.js"}
    entries = ["## INS-003: どちらにも寄らない話題"]

    assigned = classify_entries(entries, seeds, _StubEmbedder(), threshold=0.95)

    assert assigned == ["_unsorted"]


def test_classify_entries_no_seeds_goes_general():
    assigned = classify_entries(["## INS-004: x"], {}, _StubEmbedder(), threshold=0.8)
    assert assigned == ["general"]


def test_classify_entries_embed_failure_raises():
    class _Failing:
        def embed_batch(self, texts):
            return None

    with pytest.raises(RuntimeError, match="embedding failed"):
        classify_entries(["## INS-005: x"], {"backend": "db"}, _Failing(), threshold=0.8)
```

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -k classify -v`
Expected: FAIL — `ImportError: cannot import name 'classify_entries'`

- [ ] **Step 3: 実装**

`knowledge.py` の import に `from .scoring import cosine_sim, normalize` を追加し、末尾に:

```python
#: Entries whose best domain similarity falls below the threshold land here
#: rather than being dropped — losing crystallized knowledge is worse than
#: misfiling it.
UNSORTED = "_unsorted"


def classify_entries(
    entries: List[str],
    seeds: dict,
    embedder,
    threshold: float = 0.5,
) -> List[str]:
    """Assign each entry to the nearest domain by embedding similarity.

    ``seeds`` maps a domain name to representative text (typically the
    matching ``summary-<domain>.md``). No clustering and no label generation:
    the taxonomy is human-authored and only reused here, which is what keeps
    the shard labels distinguishable.
    """
    if not entries:
        return []
    if not seeds:
        return ["general"] * len(entries)

    names = sorted(seeds)
    vectors = embedder.embed_batch([seeds[n] for n in names] + list(entries))
    if vectors is None:
        raise RuntimeError("embedding failed: cannot classify knowledge entries")

    seed_vecs = [normalize(v) for v in vectors[: len(names)]]
    entry_vecs = [normalize(v) for v in vectors[len(names) :]]

    assigned: List[str] = []
    for ev in entry_vecs:
        sims = [cosine_sim(ev, sv) for sv in seed_vecs]
        best = max(range(len(sims)), key=lambda i: sims[i])
        assigned.append(names[best] if sims[best] >= threshold else UNSORTED)
    return assigned
```

- [ ] **Step 4: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_knowledge.py -k classify -v`
Expected: PASS（4 件）

- [ ] **Step 5: コミット**

```bash
git add src/cognitive_memory/knowledge.py tests/test_knowledge.py
git commit -m "feat(knowledge): 埋め込み最近傍の分野分類（ラベル生成はしない）"
```

---

## Task 11: `cogmem migrate-knowledge`

**Files:**
- Create: `src/cognitive_memory/cli/migrate_knowledge_cmd.py`
- Modify: `src/cognitive_memory/cli/main.py`
- Test: `tests/test_migrate_knowledge.py`（新規）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_migrate_knowledge.py`:

```python
"""Tests for cogmem migrate-knowledge."""

from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.cli.migrate_knowledge_cmd import migrate_knowledge


class _StubEmbedder:
    def embed_batch(self, texts):
        out = []
        for t in texts:
            lower = t.lower()
            out.append([1.0, 0.0] if "db" in lower else [0.0, 1.0])
        return out


@pytest.fixture
def flat_project(tmp_path):
    k = tmp_path / "memory" / "knowledge"
    k.mkdir(parents=True)
    (k / "summary-backend.md").write_text("db prisma の索引", encoding="utf-8")
    (k / "summary-frontend.md").write_text("ui next.js の索引", encoding="utf-8")
    (k / "insights.md").write_text(
        "# Insights\n\n"
        "## INS-001: db の接続プールは worker 数に合わせる\n"
        "- **発見**: 2026-04-02\n\n"
        "## INS-002: ui の再描画は router.refresh で引く\n"
        "- **発見**: 2026-04-03\n",
        encoding="utf-8",
    )
    return tmp_path


def _config(base: Path) -> CogMemConfig:
    return CogMemConfig(_base_dir=str(base))


def test_dry_run_writes_nothing(flat_project):
    plan = migrate_knowledge(
        _config(flat_project), kind="insights", embedder=_StubEmbedder(), dry_run=True
    )

    assert (flat_project / "memory" / "knowledge" / "insights.md").is_file()
    assert not (flat_project / "memory" / "knowledge" / "insights").exists()
    assert plan == {"INS-001": "backend", "INS-002": "frontend"}


def test_migration_creates_shards_and_preserves_entries(flat_project):
    migrate_knowledge(
        _config(flat_project), kind="insights", embedder=_StubEmbedder(), dry_run=False
    )

    d = flat_project / "memory" / "knowledge" / "insights"
    assert (d / "backend.md").is_file()
    assert (d / "frontend.md").is_file()
    assert "INS-001" in (d / "backend.md").read_text(encoding="utf-8")
    assert "INS-002" in (d / "frontend.md").read_text(encoding="utf-8")
    # 元のフラットファイルは残さない
    assert not (flat_project / "memory" / "knowledge" / "insights.md").exists()


def test_migration_is_idempotent(flat_project):
    cfg = _config(flat_project)
    migrate_knowledge(cfg, kind="insights", embedder=_StubEmbedder(), dry_run=False)

    cfg.knowledge_insights = "memory/knowledge/insights"
    before = sorted(
        (p.name, p.read_text(encoding="utf-8"))
        for p in (flat_project / "memory" / "knowledge" / "insights").glob("*.md")
    )
    migrate_knowledge(cfg, kind="insights", embedder=_StubEmbedder(), dry_run=False)
    after = sorted(
        (p.name, p.read_text(encoding="utf-8"))
        for p in (flat_project / "memory" / "knowledge" / "insights").glob("*.md")
    )

    assert before == after


def test_embed_failure_leaves_original_intact(flat_project):
    class _Failing:
        def embed_batch(self, texts):
            return None

    with pytest.raises(RuntimeError):
        migrate_knowledge(
            _config(flat_project), kind="insights", embedder=_Failing(), dry_run=False
        )

    assert (flat_project / "memory" / "knowledge" / "insights.md").is_file()
    assert not (flat_project / "memory" / "knowledge" / "insights").exists()
```

- [ ] **Step 2: テストが落ちることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_migrate_knowledge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cognitive_memory.cli.migrate_knowledge_cmd'`

- [ ] **Step 3: 実装**

`src/cognitive_memory/cli/migrate_knowledge_cmd.py`:

```python
"""`cogmem migrate-knowledge` — split a flat knowledge file into shards."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from ..config import CogMemConfig
from ..knowledge import (
    KINDS,
    UNSORTED,
    classify_entries,
    parse_knowledge_entries,
    resolve_shards,
)

_ENTRY_ID_PREFIX = {"insights": "INS", "error-patterns": "EP", "principles": "INS"}


def _domain_seeds(config: CogMemConfig) -> Dict[str, str]:
    """Read ``summary-<domain>.md`` files as classification seeds."""
    summary_dir = config.knowledge_summary_path.parent
    seeds: Dict[str, str] = {}
    if not summary_dir.is_dir():
        return seeds
    for p in sorted(summary_dir.glob("summary-*.md")):
        domain = p.stem[len("summary-") :]
        try:
            seeds[domain] = p.read_text(encoding="utf-8")
        except OSError:
            continue
    return seeds


def _git_dirty(base: Path, rel: str) -> bool:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--", rel],
            cwd=str(base),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(out.stdout.strip())


def migrate_knowledge(
    config: CogMemConfig,
    kind: str,
    embedder,
    dry_run: bool = False,
    threshold: float = 0.5,
) -> Dict[str, str]:
    """Shard ``kind`` by domain. Returns the entry-id → domain mapping.

    A no-op when the configured path is already a directory.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown knowledge kind: {kind!r}")

    configured: Path = getattr(config, KINDS[kind])
    if configured.is_dir():
        return {}
    if not configured.is_file():
        return {}

    base = Path(config._base_dir or ".")
    if not dry_run and _git_dirty(base, str(configured)):
        raise RuntimeError(
            f"{configured} has uncommitted changes. Commit or stash first — "
            "migration rewrites this file and would swallow pending appends."
        )

    text = configured.read_text(encoding="utf-8")
    entries = list(parse_knowledge_entries(text, configured, config.knowledge_arousal))
    if not entries:
        return {}

    contents = [e.content for e in entries]
    domains = classify_entries(contents, _domain_seeds(config), embedder, threshold)

    prefix = _ENTRY_ID_PREFIX[kind]
    plan: Dict[str, str] = {}
    buckets: Dict[str, list] = {}
    for entry, domain in zip(entries, domains):
        first_line = entry.content.split("\n", 1)[0]
        entry_id = first_line.split(":", 1)[0].removeprefix("## ").strip()
        if not entry_id.startswith(prefix):
            entry_id = first_line.strip()
        plan[entry_id] = domain
        buckets.setdefault(domain, []).append(entry.content)

    if dry_run:
        return plan

    target_dir = configured.with_suffix("")
    target_dir.mkdir(parents=True, exist_ok=True)

    # Write to .tmp siblings first, then rename, so a mid-run failure
    # leaves the original untouched.
    written: list = []
    try:
        for domain, blocks in buckets.items():
            body = f"# {kind} — {domain}\n\n" + "\n\n".join(blocks) + "\n"
            tmp = target_dir / f"{domain}.md.tmp"
            tmp.write_text(body, encoding="utf-8")
            written.append((tmp, target_dir / f"{domain}.md"))
        for tmp, final in written:
            tmp.replace(final)
    except OSError:
        for tmp, _ in written:
            tmp.unlink(missing_ok=True)
        raise

    configured.unlink()
    return plan


def run_migrate_knowledge(
    kind: str = "all", dry_run: bool = False, config: Optional[CogMemConfig] = None
) -> int:
    """CLI entry point."""
    config = config or CogMemConfig.load()
    from ..store import MemoryStore

    store = MemoryStore(config)
    kinds = sorted(KINDS) if kind == "all" else [kind]

    for k in kinds:
        try:
            plan = migrate_knowledge(config, k, store.embedder, dry_run=dry_run)
        except (RuntimeError, ValueError) as e:
            print(f"[ERROR] {k}: {e}", file=sys.stderr)
            return 1
        if not plan:
            print(f"{k}: nothing to migrate")
            continue
        label = "would move" if dry_run else "moved"
        for entry_id, domain in sorted(plan.items()):
            marker = "  (UNSORTED)" if domain == UNSORTED else ""
            print(f"  {label} {entry_id} -> {k}/{domain}.md{marker}")
        print(f"{k}: {len(plan)} entries across {len(set(plan.values()))} shards")

    if not dry_run:
        print("\nNext: update cogmem.toml to point at the directory, e.g.")
        print('  [cogmem.knowledge]')
        print('  insights = "memory/knowledge/insights"')
    store.close()
    return 0
```

- [ ] **Step 4: CLI に配線**

`src/cognitive_memory/cli/main.py` に、既存のサブコマンド定義と同じ書式で追加する。既存の `migrate` サブコマンドの定義箇所を `grep -n "migrate" src/cognitive_memory/cli/main.py` で探し、その隣に同じ形で:

```python
    p_mk = subparsers.add_parser(
        "migrate-knowledge", help="Split a flat knowledge file into per-domain shards"
    )
    p_mk.add_argument(
        "--kind", default="all",
        choices=["all", "insights", "error-patterns", "principles"],
    )
    p_mk.add_argument("--dry-run", action="store_true")
```

ディスパッチ側に:

```python
    if args.command == "migrate-knowledge":
        from .migrate_knowledge_cmd import run_migrate_knowledge
        return run_migrate_knowledge(kind=args.kind, dry_run=args.dry_run)
```

- [ ] **Step 5: テストが通ることを確認**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_migrate_knowledge.py -v`
Expected: PASS（5 件）

- [ ] **Step 6: CLI を手で確認**

```bash
cd /tmp && rm -rf mk-demo && mkdir mk-demo && cd mk-demo
mkdir -p memory/knowledge
printf 'db prisma の索引\n' > memory/knowledge/summary-backend.md
printf '# Insights\n\n## INS-001: db の接続プール設定を worker 数に合わせる\n- **発見**: 2026-04-02\n' > memory/knowledge/insights.md
PYTHONPATH=/Users/akira/workspace/ai-dev/cognitive-memory-lib/src \
  /Users/akira/workspace/ai-dev/cognitive-memory-lib/.venv/bin/python -m cognitive_memory.cli.main migrate-knowledge --kind insights --dry-run
```

Expected: `would move INS-001 -> insights/backend.md` が出て、`memory/knowledge/insights.md` が残っていること。

- [ ] **Step 7: コミット**

```bash
git add src/cognitive_memory/cli/migrate_knowledge_cmd.py src/cognitive_memory/cli/main.py tests/test_migrate_knowledge.py
git commit -m "feat(cli): cogmem migrate-knowledge を追加（dry-run / dirty guard / atomic rename）"
```

---

## Task 12: crystallize / wrap テンプレートの更新（P5 修正込み）

**Files:**
- Modify: `src/cognitive_memory/templates/skills/crystallize/SKILL.md`
- Modify: `src/cognitive_memory/templates/ja/skills/crystallize/SKILL.md`
- Modify: `src/cognitive_memory/templates/{,ja/}skills/wrap/SKILL.md`

**背景（P5）:** ja 版 crystallize の記述が `memory/knowledge/error-patterns.md`（44行目）と `memory/error-patterns.md`（58行目）で食い違い、`memory/insights.md`（45, 63行目）は config 既定の `memory/knowledge/insights.md` と別物を指している。ember には両方のファイルが実在する（4,480 byte と 15,314 byte）。

- [ ] **Step 1: 現状の記述を確認**

```bash
grep -n "insights.md\|error-patterns.md" \
  src/cognitive_memory/templates/skills/crystallize/SKILL.md \
  src/cognitive_memory/templates/ja/skills/crystallize/SKILL.md
```

- [ ] **Step 2: パスを `memory/knowledge/` に統一**

両方の crystallize テンプレートで、`memory/insights.md` → `memory/knowledge/insights.md`、`memory/error-patterns.md` → `memory/knowledge/error-patterns.md` に統一する。

- [ ] **Step 3: 追記手順をシャード対応にする**

crystallize の追記ステップを次の手順に差し替える（ja 版は日本語で同内容）:

```markdown
### 追記先の決定

1. `cogmem signals --json` の `knowledge_health.legacy_kinds` を見る
   - その kind が含まれていれば単一ファイル運用。従来通り `memory/knowledge/<kind>.md` に追記する
   - 含まれていなければシャード運用。次へ
2. `memory/knowledge/summary.md` の「索引の地図」で分野を選ぶ（索引と本文で同じ判断を一度だけ行う）
3. 本文を `memory/knowledge/<kind>/<分野>.md` の末尾に追記する
4. 索引 1 行を `memory/knowledge/summary-<分野>.md` に追記する

**1 回の追記が触るファイルは、本文 1 つと索引 1 つだけ。**
採番レジストリのような「全追記が触る共有ファイル」を作らないこと。
並列セッションの衝突を別の場所に作り直すことになる。
```

- [ ] **Step 4: 重複チェックを意味検索に変更**

crystallize の重複チェック手順を差し替える:

```markdown
### 重複チェック

`cogmem search "<新エントリの要旨>" --json` を使う。knowledge は索引済みなので、
既存の INS/EP が意味的に近ければ結果に出る（`kind` が `knowledge` の行）。
肥大ファイルへの grep は不要。
```

- [ ] **Step 5: 番号採番の記述を更新**

「末尾 N 行を Read して直近番号を確認」を次に差し替える:

```markdown
新しい番号は `cogmem signals --json` の `knowledge_health.shards` に出ているシャードを
横断して決まる。手で末尾を読む必要はない。
```

- [ ] **Step 6: 反映を確認**

```bash
grep -rn "memory/insights.md\|memory/error-patterns.md" src/cognitive_memory/templates/ || echo "OK: 旧パス残存なし"
```

Expected: `OK: 旧パス残存なし`

- [ ] **Step 7: コミット**

```bash
git add src/cognitive_memory/templates/
git commit -m "fix(skills): crystallize のパス split-brain を修正し、シャード追記と意味検索による重複チェックに変更"
```

---

## Task 13: ドキュメント / CHANGELOG / バージョン

**Files:**
- Modify: `docs/configuration.md`, `docs/cli-reference.md`, `CHANGELOG.md`, `src/cognitive_memory/_version.py`, `README.md`, `README_ja.md`

- [ ] **Step 1: 設定リファレンスを更新**

`docs/configuration.md` の `[cogmem.knowledge]` セクションに追記:

```markdown
| キー | 既定値 | 説明 |
|---|---|---|
| `principles` | `memory/knowledge/principles.md` | 原則本文。ファイル or ディレクトリ |
| `arousal` | `0.6` | knowledge 行に与える arousal。時間減衰は掛からない |
| `shard_warn_kb` | `64` | シャード 1 枚の警告しきい値。**上限ではない**（本文は索引の逃がし先なので受け止める側） |

`summary` / `error_patterns` / `insights` / `principles` は**ファイルでもディレクトリでも指せる**。
ディレクトリを指すと配下の `*.md` が分野別シャードとして扱われる。
```

- [ ] **Step 2: CLI リファレンスを更新**

`docs/cli-reference.md` に追記:

```markdown
### `cogmem migrate-knowledge`

フラットな knowledge ファイルを分野別シャードに分割する。

```bash
cogmem migrate-knowledge --kind insights --dry-run   # 対応表を確認
cogmem migrate-knowledge --kind all                  # 適用
```

分野は `memory/knowledge/summary-<分野>.md` をシードにした埋め込み最近傍で決まる。
似た分野が無いエントリは `_unsorted.md` に退避される（捨てない）。
`memory/knowledge/` に未コミットの変更があると実行を拒否する。
```

- [ ] **Step 3: CHANGELOG を書く**

`CHANGELOG.md` の先頭に追加:

```markdown
## 0.34.0

### Added
- knowledge（insights / error-patterns / principles）が `vectors.db` の索引対象になった。
  **既定で ON** — recall の結果に結晶化知識が混ざるようになる（`kind` フィールドで区別可能）
- 結晶化知識には時間減衰を掛けない。ログだけが減衰する
- `cogmem migrate-knowledge` — フラットな knowledge ファイルを分野別シャードに分割
- `knowledge_health` を `cogmem signals` が報告（シャード別サイズ・レガシー運用の検出）
- 設定キー `[cogmem.knowledge]` に `principles` / `arousal` / `shard_warn_kb`

### Fixed
- ログの再索引が、同じ日付を持つ knowledge 行を stale として巻き込んで削除していた
- `indexed_files` の PK が basename のみだったため、`logs/x.md` と `knowledge/insights/x.md` が衝突していた
- crystallize スキルの追記先が `memory/insights.md` と `memory/knowledge/insights.md` で
  食い違っていた（split-brain。両方のファイルが実在するプロジェクトがあった）

### Notes
- `knowledge.*` 設定はファイルでもディレクトリでも指せる。既存のフラット運用は変更なしで動作する
- シャードにサイズ上限は掛からない。警告のみ（本文は索引の逃がし先であり、上限を置くと行き先が無くなる）
```

- [ ] **Step 4: バージョンを上げる**

`src/cognitive_memory/_version.py` を `0.34.0` にする。

- [ ] **Step 5: 全テストを流す**

Run: `PYTHONPATH=src .venv/bin/pytest tests/ -q`
Expected: PASS（全件）

- [ ] **Step 6: コミット**

```bash
git add docs/ CHANGELOG.md src/cognitive_memory/_version.py README.md README_ja.md
git commit -m "docs: knowledge sharding のドキュメントと 0.34.0 CHANGELOG"
```

---

## リリース

`cogmem-release` スキルの手順に従う（バージョンバンプ済みなので Step 1 は完了扱い）。

## 実データでの検証（リリース前）

```bash
cd /Users/akira/workspace/benchmark_app
git status --porcelain memory/knowledge/     # クリーンであること

# 1. dry-run で対応表を目視
cogmem migrate-knowledge --kind all --dry-run | tee /tmp/mk-plan.txt
grep -c UNSORTED /tmp/mk-plan.txt            # _unsorted 行き件数を確認

# 2. 適用して索引
cogmem migrate-knowledge --kind all
cogmem index --force

# 3. 検索で knowledge が引けることを確認
cogmem search "pg-boss の compensation" --json | head -40
```

**確認項目:**
- 149 件の INS と 117 件の EP が、移行前後で件数一致すること
- `_unsorted.md` の件数が全体の 1 割を超えていたら threshold を上げ直す
- `cogmem search` の結果に `"kind": "knowledge"` の行が含まれること
