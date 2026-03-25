"""Tests for skill export/import with YAML frontmatter."""

from __future__ import annotations

from pathlib import Path

from cognitive_memory.cli.skills_cmd import _skill_to_markdown, _parse_skill_markdown
from cognitive_memory.skills.types import Skill, UsageStats, SuccessMetric


def _make_skill(**overrides) -> Skill:
    defaults = dict(
        id="skill_123_abc",
        name="Test Skill",
        category="conversation-skills",
        description="テスト用スキルの説明文",
        execution_pattern="1. Step one\n2. Step two\n3. Step three",
        success_metrics=[
            SuccessMetric(
                name="Effectiveness",
                description="Overall success",
                measurement_method="feedback",
                target_value=0.8,
                current_value=0.6,
            )
        ],
        improvement_history=[],
        usage_stats=UsageStats(
            total_executions=10,
            successful_executions=8,
            average_effectiveness=0.75,
            last_used_at="2026-03-25",
            frequency=0.5,
        ),
        created_at="2026-03-20",
        updated_at="2026-03-25",
        version=3,
    )
    defaults.update(overrides)
    return Skill(**defaults)


class TestSkillToMarkdown:
    def test_has_yaml_frontmatter(self):
        md = _skill_to_markdown(_make_skill())
        assert md.startswith("---\n")
        assert "\n---\n" in md

    def test_frontmatter_contains_description(self):
        md = _skill_to_markdown(_make_skill(description="カレンダー登録スキル"))
        lines = md.split("\n")
        assert lines[0] == "---"
        assert lines[1] == "description: カレンダー登録スキル"
        assert lines[2] == "---"

    def test_no_trigger_section(self):
        md = _skill_to_markdown(_make_skill())
        assert "## トリガー" not in md
        assert "## Triggers" not in md

    def test_has_steps_section(self):
        md = _skill_to_markdown(_make_skill())
        assert "## 手順" in md

    def test_has_metadata(self):
        md = _skill_to_markdown(_make_skill())
        assert "Effectiveness: 0.75" in md
        assert "Version: 3" in md
        assert "Skill ID: skill_123_abc" in md


class TestParseSkillMarkdown:
    def test_parse_frontmatter(self, tmp_path):
        content = """---
description: テスト用スキル
---

# テストスキル

## 手順
1. Do something
"""
        fp = tmp_path / "test-skill.md"
        fp.write_text(content, encoding="utf-8")
        result = _parse_skill_markdown(fp)
        assert result["description"] == "テスト用スキル"
        assert result["name"] == "テストスキル"

    def test_parse_legacy_triggers(self, tmp_path):
        content = """# レガシースキル

## トリガー
- 条件A
- 条件B

## 手順
1. Step one
"""
        fp = tmp_path / "legacy.md"
        fp.write_text(content, encoding="utf-8")
        result = _parse_skill_markdown(fp)
        assert result["description"] == "条件A. 条件B"

    def test_frontmatter_takes_precedence_over_triggers(self, tmp_path):
        content = """---
description: frontmatterの説明
---

# 混在スキル

## トリガー
- レガシー条件

## 手順
1. Step
"""
        fp = tmp_path / "mixed.md"
        fp.write_text(content, encoding="utf-8")
        result = _parse_skill_markdown(fp)
        assert result["description"] == "frontmatterの説明"

    def test_parse_skill_id(self, tmp_path):
        content = """---
description: test
---

# Skill
*Skill ID: skill_999_xyz*

## 手順
1. Do it
"""
        fp = tmp_path / "with-id.md"
        fp.write_text(content, encoding="utf-8")
        result = _parse_skill_markdown(fp)
        assert result["skill_id"] == "skill_999_xyz"


class TestRoundTrip:
    def test_export_then_import_preserves_description(self, tmp_path):
        original = _make_skill(description="往復テスト: 記憶検索スキル")
        md = _skill_to_markdown(original)
        fp = tmp_path / "roundtrip.md"
        fp.write_text(md, encoding="utf-8")
        parsed = _parse_skill_markdown(fp)
        assert parsed["description"] == "往復テスト: 記憶検索スキル"
        assert parsed["name"] == "Test Skill"
        assert parsed["skill_id"] == "skill_123_abc"
