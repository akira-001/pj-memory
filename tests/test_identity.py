"""Identity file read/write tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_memory.identity import (
    parse_identity_md,
    write_identity_md,
    update_identity_section,
    detect_placeholder_sections,
)


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


class TestUpdateIdentitySection:
    def test_update_existing_section(self, tmp_path):
        md = tmp_path / "user.md"
        md.write_text(
            "# User\n\n## 基本情報\n- 名前:\n- 役割:\n\n## 専門性\n[会話から観察された内容]\n",
            encoding="utf-8",
        )
        update_identity_section(md, "基本情報", "- 名前: Akira\n- 役割: コンサルタント")
        result = parse_identity_md(md)
        assert "Akira" in result["sections"]["基本情報"]
        assert "コンサルタント" in result["sections"]["基本情報"]

    def test_add_new_section(self, tmp_path):
        md = tmp_path / "user.md"
        md.write_text("# User\n\n## 基本情報\nTest\n", encoding="utf-8")
        update_identity_section(md, "新セクション", "新しい内容")
        result = parse_identity_md(md)
        assert result["sections"]["新セクション"] == "新しい内容"
        assert result["sections"]["基本情報"] == "Test"

    def test_overwrite_existing_data(self, tmp_path):
        md = tmp_path / "user.md"
        md.write_text("# User\n\n## 専門性\nPython, SQL\n", encoding="utf-8")
        update_identity_section(md, "専門性", "Python, SQL, Go")
        result = parse_identity_md(md)
        assert "Go" in result["sections"]["専門性"]

    def test_file_not_exists_creates(self, tmp_path):
        md = tmp_path / "identity" / "user.md"
        update_identity_section(md, "基本情報", "- 名前: Akira")
        assert md.exists()
        result = parse_identity_md(md)
        assert "Akira" in result["sections"]["基本情報"]


class TestDetectPlaceholderUser:
    """user.md のプレースホルダー検知。"""

    def test_template_all_placeholder(self, tmp_path):
        """テンプレートそのまま → 全セクションがプレースホルダー。"""
        md = tmp_path / "user.md"
        md.write_text(
            "# ユーザープロファイル\n\n"
            "## 基本情報\n- 名前:\n- 役割:\n- タイムゾーン:\n\n"
            "## 専門性\n[会話から観察された内容]\n\n"
            "## コミュニケーション好み\n[会話から観察された内容]\n\n"
            "## 意思決定パターン\n[会話から観察された内容]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert result["基本情報"] is True
        assert result["専門性"] is True
        assert result["コミュニケーション好み"] is True
        assert result["意思決定パターン"] is True

    def test_template_en_all_placeholder(self, tmp_path):
        """英語テンプレートも検知できる。"""
        md = tmp_path / "user.md"
        md.write_text(
            "# User Profile\n\n"
            "## Basic Info\n- Name:\n- Role:\n- Timezone:\n\n"
            "## Expertise\n[Observed from conversations]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert result["Basic Info"] is True
        assert result["Expertise"] is True

    def test_partially_filled(self, tmp_path):
        """一部だけ記入済み → 記入済みセクションは False。"""
        md = tmp_path / "user.md"
        md.write_text(
            "# ユーザープロファイル\n\n"
            "## 基本情報\n- 名前: Akira\n- 役割: コンサルタント\n- タイムゾーン: Asia/Tokyo\n\n"
            "## 専門性\n[会話から観察された内容]\n\n"
            "## コミュニケーション好み\n簡潔・結論ファースト\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert result["基本情報"] is False
        assert result["専門性"] is True
        assert result["コミュニケーション好み"] is False

    def test_fully_filled(self, tmp_path):
        """全セクション記入済み → 全て False。"""
        md = tmp_path / "user.md"
        md.write_text(
            "# ユーザープロファイル\n\n"
            "## 基本情報\n- 名前: Akira\n- 役割: コンサルタント\n\n"
            "## 専門性\nPython, 経営戦略\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert all(v is False for v in result.values())

    def test_empty_value_after_colon(self, tmp_path):
        """コロン後が空 → プレースホルダー扱い。"""
        md = tmp_path / "user.md"
        md.write_text(
            "# User\n\n## 基本情報\n- 名前:\n- 役割: コンサルタント\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        # セクション全体に1つでも空フィールドがあればプレースホルダー
        assert result["基本情報"] is True

    def test_file_not_exists(self, tmp_path):
        """ファイル未存在 → 空 dict。"""
        result = detect_placeholder_sections(tmp_path / "nope.md")
        assert result == {}


class TestDetectPlaceholderSoul:
    """soul.md のプレースホルダー検知。"""

    def test_template_all_placeholder(self, tmp_path):
        """テンプレートそのまま → 全セクションがプレースホルダー。"""
        md = tmp_path / "soul.md"
        md.write_text(
            "# Soul — エージェントのアイデンティティ\n\n"
            "## 役割\n[このプロジェクトにおけるエージェントの役割を記述]\n"
            "例: 開発パートナー、批判的思考パートナー\n\n"
            "## 核心的価値観\n1. [このエージェントが何を信じるか]\n"
            "例: 真実を語る\n\n"
            "## コミュニケーションスタイル\n"
            "- 言語: [日本語 / 英語 / 等]\n"
            "- トーン: [カジュアル / フォーマル / 等]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert result["役割"] is True
        assert result["核心的価値観"] is True
        assert result["コミュニケーションスタイル"] is True

    def test_template_en_all_placeholder(self, tmp_path):
        """英語テンプレート。"""
        md = tmp_path / "soul.md"
        md.write_text(
            "# Soul — Agent Identity\n\n"
            "## Role\n[What is this agent's role in the project?]\n"
            "e.g., Development partner\n\n"
            "## Core Values\n1. [What does this agent believe in?]\n"
            "e.g., Truth over comfort\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert result["Role"] is True
        assert result["Core Values"] is True

    def test_filled_soul(self, tmp_path):
        """実データ入り → False。"""
        md = tmp_path / "soul.md"
        md.write_text(
            "# Soul\n\n"
            "## 役割\n開発パートナー、批判的思考パートナー\n\n"
            "## 核心的価値観\n1. 事実のみ報告\n2. 根拠ベースの思考\n\n"
            "## コミュニケーションスタイル\n- 言語: 日本語\n- トーン: カジュアル\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert all(v is False for v in result.values())

    def test_example_lines_only_are_placeholder(self, tmp_path):
        """「例:」行しかない場合もプレースホルダー。"""
        md = tmp_path / "soul.md"
        md.write_text(
            "# Soul\n\n"
            "## やらないこと\n"
            "例: 根拠なしの楽観、アイデアの即座な全肯定\n"
            "例: ユーザーの思考を代替しない\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert result["やらないこと"] is True


class TestDetectPlaceholderAgents:
    """agents.md のプレースホルダー検知。

    agents.md はプロトコル定義ファイルなので、
    soul/user と違い「テンプレートのまま」かどうかではなく、
    カスタマイズ済みかどうかを検知する。
    Session Init / Wrap / Live Logging の各セクションが
    プロジェクト固有の設定を含んでいるかを判定。
    """

    def test_template_agents(self, tmp_path):
        """テンプレートそのまま → プレースホルダー。"""
        md = tmp_path / "agents.md"
        md.write_text(
            "# Agents — Behavior Rules & Logging Protocol\n\n"
            "## Auto-Execution Rules\n\n"
            "Execute \"Session Init\" immediately after loading this file.\n\n"
            "## Session Init\n\n"
            "[Configure your Session Init steps here]\n\n"
            "## Live Logging\n\n"
            "[Configure your logging triggers here]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert result["Session Init"] is True
        assert result["Live Logging"] is True

    def test_customized_agents(self, tmp_path):
        """カスタマイズ済み → False。"""
        md = tmp_path / "agents.md"
        md.write_text(
            "# Agents — 行動ルール\n\n"
            "## Session Init\n\n"
            "Step 1: memory/contexts/YYYY-MM-DD.md を Read する\n"
            "Step 2: memory/logs/ の直近2ファイルを確認\n\n"
            "## Live Logging\n\n"
            "重要な瞬間に memory/logs/YYYY-MM-DD.md に即座に追記する。\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(md)
        assert result["Session Init"] is False
        assert result["Live Logging"] is False
