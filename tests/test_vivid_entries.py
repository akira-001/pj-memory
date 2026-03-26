"""Tests for vivid (high-arousal, multi-line) log entry parsing."""

from __future__ import annotations

from cognitive_memory.parser import parse_entries


VIVID_LOG = """\
# 2026-03-26 セッションログ

## セッション概要

## ログエントリ

### [INSIGHT] 3段階記憶モデルの設計
*Arousal: 0.9 | Emotion: Discovery*
Akira が「人間の記憶に近づけたい」と言ったことがきっかけ。
最初は compact のタイミング制御だけ考えていたが、
「鮮明な記憶はなぜ鮮明か」を掘り下げるうちに
忘却曲線と想起の関係に行き着いた。
鮮明（直近1週間、高解像度）→ 薄れる（1-4週間、compact）
→ 定着（4週間〜、記憶の定着で抽象ルール化）。
Arousal が忘却速度を制御し、想起が arousal を引き上げて
忘却曲線をリセットする — 「何度も思い出す記憶は定着する」。
recall_count + arousal boost で実装する方針に決定。

---

### [DECISION] 結晶化 → 記憶の定着に用語変更
*Arousal: 0.5 | Emotion: Refinement*
agents.md、summary.md、i18n の全箇所で用語を統一。

---

### [MILESTONE] ダッシュボード「記憶の定着」ページ実装
*Arousal: 0.8 | Emotion: Achievement*
元々「結晶化（Crystallization）」と呼んでいた機能のダッシュボードページ。
Akira が「結晶化という名前がピンとこない」と言ったのがきっかけで
同日に用語変更を決定し、コード側は最初から「記憶の定着」で統一した。
TDD で21テスト、シグナル表・チェックポイント・エラーパターン一覧を表示。
EN/JA i18n 対応。

---

## 引き継ぎ
"""

SHORT_LOG = """\
# 2026-03-26 セッションログ

## セッション概要

## ログエントリ

### [QUESTION] cogmem の精度測定方法
*Arousal: 0.4 | Emotion: Curiosity*
定量的な測定方法が未定。

---

## 引き継ぎ
"""


TEST_DATE = "2026-03-26"


class TestVividEntryParsing:
    """Vivid (high-arousal) entries are parsed with full content."""

    def test_10_line_entry_parsed_completely(self):
        """A 10-line high-arousal entry preserves all content."""
        entries = list(parse_entries(VIVID_LOG, date=TEST_DATE))
        insight = [e for e in entries if "3段階記憶モデル" in e.content][0]
        assert insight.arousal == 0.9
        assert insight.category == "INSIGHT"
        # All 10 lines of content should be present
        assert "recall_count + arousal boost" in insight.content
        assert "忘却曲線をリセット" in insight.content
        assert "きっかけ" in insight.content

    def test_vivid_entry_preserves_user_quote(self):
        """User quotes in vivid entries are preserved."""
        entries = list(parse_entries(VIVID_LOG, date=TEST_DATE))
        milestone = [e for e in entries if "ダッシュボード" in e.content][0]
        assert "結晶化という名前がピンとこない" in milestone.content

    def test_vivid_entry_preserves_prior_names(self):
        """Prior names / aliases in vivid entries are preserved."""
        entries = list(parse_entries(VIVID_LOG, date=TEST_DATE))
        milestone = [e for e in entries if "ダッシュボード" in e.content][0]
        assert "結晶化（Crystallization）" in milestone.content

    def test_mixed_arousal_entries_all_parsed(self):
        """Log with mixed arousal levels parses all entries."""
        entries = list(parse_entries(VIVID_LOG, date=TEST_DATE))
        assert len(entries) == 3
        arousals = sorted([e.arousal for e in entries])
        assert arousals == [0.5, 0.8, 0.9]

    def test_short_entry_unchanged(self):
        """Low-arousal short entries still parse correctly."""
        entries = list(parse_entries(SHORT_LOG, date=TEST_DATE))
        assert len(entries) == 1
        assert entries[0].arousal == 0.4
        assert entries[0].category == "QUESTION"

    def test_vivid_content_line_count(self):
        """High-arousal entry has significantly more content than low-arousal."""
        vivid = list(parse_entries(VIVID_LOG, date=TEST_DATE))
        short = list(parse_entries(SHORT_LOG, date=TEST_DATE))
        insight = [e for e in vivid if e.category == "INSIGHT"][0]
        question = short[0]
        # Vivid entry should have more content lines
        vivid_lines = len(insight.content.strip().splitlines())
        short_lines = len(question.content.strip().splitlines())
        assert vivid_lines >= 5
        assert short_lines <= 3
