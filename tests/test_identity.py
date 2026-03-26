"""Identity file read/write tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_memory.identity import parse_identity_md, write_identity_md


class TestParseIdentityMd:
    def test_parse_sections(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "# Title\n\n## Section A\nContent A\n\n## Section B\nLine 1\nLine 2\n",
            encoding="utf-8",
        )
        result = parse_identity_md(md)
        assert result["title"] == "Title"
        assert result["sections"]["Section A"] == "Content A"
        assert "Line 1" in result["sections"]["Section B"]

    def test_parse_missing_file(self, tmp_path):
        result = parse_identity_md(tmp_path / "nope.md")
        assert result["title"] == ""
        assert result["sections"] == {}

    def test_parse_preserves_frontmatter(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "*自動更新*\n\n# Title\n\n## Sec\nContent\n",
            encoding="utf-8",
        )
        result = parse_identity_md(md)
        assert result["preamble"] == "*自動更新*"
        assert result["title"] == "Title"


class TestWriteIdentityMd:
    def test_roundtrip(self, tmp_path):
        md = tmp_path / "test.md"
        original = "# Title\n\n## Sec A\nContent A\n\n## Sec B\nContent B\n"
        md.write_text(original, encoding="utf-8")
        data = parse_identity_md(md)
        write_identity_md(md, data)
        result = parse_identity_md(md)
        assert result["sections"] == data["sections"]
        assert result["title"] == data["title"]

    def test_write_with_preamble(self, tmp_path):
        md = tmp_path / "test.md"
        data = {
            "title": "User",
            "preamble": "*自動更新*",
            "sections": {"基本情報": "- 名前: Akira"},
        }
        write_identity_md(md, data)
        text = md.read_text(encoding="utf-8")
        assert text.startswith("*自動更新*\n")
        assert "# User" in text
        assert "## 基本情報" in text
        assert "- 名前: Akira" in text

    def test_write_empty_sections(self, tmp_path):
        md = tmp_path / "test.md"
        data = {"title": "Empty", "preamble": "", "sections": {}}
        write_identity_md(md, data)
        text = md.read_text(encoding="utf-8")
        assert "# Empty" in text

    def test_write_no_title(self, tmp_path):
        md = tmp_path / "test.md"
        data = {"title": "", "preamble": "", "sections": {"Sec": "Content"}}
        write_identity_md(md, data)
        text = md.read_text(encoding="utf-8")
        assert "## Sec" in text
        assert "Content" in text
