"""Tests for parser module: parse_entries, is_noise, arousal parsing."""

import pytest

from cognitive_memory.parser import is_noise, parse_entries


class TestIsNoise:
    def test_short_content_is_noise(self):
        assert is_noise("了解") is True
        assert is_noise("OK") is True

    def test_below_min_length_is_noise(self):
        assert is_noise("短い") is True  # < 20 chars

    def test_normal_content_not_noise(self):
        assert is_noise("これは十分な長さのコンテンツで、ノイズではないはずです") is False

    def test_noise_pattern_match(self):
        assert is_noise("情報がありません。このエントリは何も含んでいません。") is True

    def test_empty_string_is_noise(self):
        assert is_noise("") is True
        assert is_noise("   ") is True


class TestParseEntries:
    SAMPLE_LOG = """# 2026-03-21 セッションログ

## セッション概要
テスト用

## ログエントリ

### [INSIGHT][TECH] テスト洞察
*Arousal: 0.7 | Emotion: Clarity*
これはテスト用の洞察エントリ。十分な長さが必要。

---

### [DECISION][TECH] テスト決定
*Arousal: 0.6 | Emotion: Determination*
これはテスト用の決定エントリ。十分な長さが必要。

---

## 引き継ぎ
- この内容は検索対象外
- 引き継ぎのテスト
"""

    def test_excludes_handover_section(self):
        entries = list(parse_entries(self.SAMPLE_LOG, "2026-03-21"))
        contents = [e.content for e in entries]
        assert not any("検索対象外" in c for c in contents)

    def test_extracts_entries_correctly(self):
        entries = list(parse_entries(self.SAMPLE_LOG, "2026-03-21"))
        assert len(entries) == 2
        assert entries[0].arousal == 0.7
        assert entries[1].arousal == 0.6
        assert entries[0].date == "2026-03-21"

    def test_custom_handover_delimiter(self):
        md = """### [INSIGHT] Test entry with enough content length
*Arousal: 0.5 | Emotion: Insight*
Some content here that is long enough to pass filter.

---

## Custom Delimiter
This should be excluded.
"""
        entries = list(
            parse_entries(md, "2026-01-01", handover_delimiter="## Custom Delimiter")
        )
        assert len(entries) == 1
        assert "excluded" not in entries[0].content

    def test_missing_arousal_defaults_to_05(self):
        md = """### [INSIGHT][TECH] No arousal tag entry
This entry has no arousal tag but is long enough to pass the noise filter and indexing."""
        entries = list(parse_entries(md, "2026-03-21"))
        assert len(entries) == 1
        assert entries[0].arousal == 0.5

    def test_invalid_arousal_defaults_to_05(self):
        md = """### [INSIGHT][TECH] Bad arousal tag entry
*Arousal: notanumber | Emotion: Confusion*
This entry has an invalid arousal value but enough content."""
        entries = list(parse_entries(md, "2026-03-21"))
        assert len(entries) == 1
        assert entries[0].arousal == 0.5

    def test_no_entries_yields_nothing(self):
        md = "# Just a title\nSome text without entries."
        entries = list(parse_entries(md, "2026-01-01"))
        assert entries == []

    def test_noise_entries_filtered(self):
        md = """### [INSIGHT] OK

---

### [INSIGHT][TECH] Real entry with sufficient content
*Arousal: 0.8 | Emotion: Insight*
This is a real entry with enough content to pass the noise filter."""
        entries = list(parse_entries(md, "2026-01-01"))
        assert len(entries) == 1
        assert entries[0].arousal == 0.8


class TestCategoryExtraction:
    """Tests for category tag extraction."""

    def test_extracts_insight_category(self):
        md = "### [INSIGHT][TECH] Discovery\n*Arousal: 0.8 | Emotion: Insight*\nSome insight content here.\n---"
        entries = list(parse_entries(md, "2026-03-21"))
        assert len(entries) == 1
        assert entries[0].category == "INSIGHT"

    def test_extracts_error_category(self):
        md = "### [ERROR] Wrong assumption\n*Arousal: 0.7 | Emotion: Conflict*\nAssumption was wrong.\n---"
        entries = list(parse_entries(md, "2026-03-21"))
        assert len(entries) == 1
        assert entries[0].category == "ERROR"

    def test_no_category_tag(self):
        md = "### Plain title without tags\n*Arousal: 0.5 | Emotion: Neutral*\nSome content that is long enough.\n---"
        entries = list(parse_entries(md, "2026-03-21"))
        assert len(entries) == 1
        assert entries[0].category is None

    def test_multiple_tags_uses_first(self):
        md = "### [PATTERN][MARKET] Recurring theme\n*Arousal: 0.7 | Emotion: Recognition*\nThis theme keeps coming up again.\n---"
        entries = list(parse_entries(md, "2026-03-21"))
        assert len(entries) == 1
        assert entries[0].category == "PATTERN"
