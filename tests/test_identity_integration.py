# tests/test_identity_integration.py
"""Identity update integration tests using session log fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_memory.identity import (
    detect_placeholder_sections,
    parse_identity_md,
    update_identity_section,
)

FIXTURES = Path(__file__).parent / "fixtures" / "session_logs"


class TestUserExpertiseUpdate:
    """user_expertise.md: Go/gRPC/dagster の専門性 → user.md 専門性を更新。"""

    def test_detect_before_update(self, tmp_path):
        user_md = tmp_path / "user.md"
        user_md.write_text(
            "# ユーザープロファイル\n\n## 専門性\n[会話から観察された内容]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(user_md)
        assert result["専門性"] is True

    def test_update_from_log(self, tmp_path):
        user_md = tmp_path / "user.md"
        user_md.write_text(
            "# ユーザープロファイル\n\n## 専門性\n[会話から観察された内容]\n",
            encoding="utf-8",
        )
        update_identity_section(
            user_md, "専門性",
            "- Go（10年）、pprof によるヒープ分析\n- gRPC（社内マイクロサービス）\n- dagster（ETL パイプライン）",
        )
        result = detect_placeholder_sections(user_md)
        assert result["専門性"] is False
        data = parse_identity_md(user_md)
        assert "Go" in data["sections"]["専門性"]
        assert "gRPC" in data["sections"]["専門性"]

    def test_log_fixture_exists(self):
        assert (FIXTURES / "user_expertise.md").exists()


class TestUserBasicInfoUpdate:
    """user_basic_info.md: 名前/役割/TZ → user.md 基本情報を更新。"""

    def test_detect_empty_fields(self, tmp_path):
        user_md = tmp_path / "user.md"
        user_md.write_text(
            "# ユーザープロファイル\n\n## 基本情報\n- 名前:\n- 役割:\n- タイムゾーン:\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(user_md)
        assert result["基本情報"] is True

    def test_update_from_log(self, tmp_path):
        user_md = tmp_path / "user.md"
        user_md.write_text(
            "# ユーザープロファイル\n\n## 基本情報\n- 名前:\n- 役割:\n- タイムゾーン:\n",
            encoding="utf-8",
        )
        update_identity_section(
            user_md, "基本情報",
            "- 名前: 田中太郎\n- 役割: CTO（SaaS スタートアップ）\n- タイムゾーン: Asia/Tokyo (JST)",
        )
        result = detect_placeholder_sections(user_md)
        assert result["基本情報"] is False
        data = parse_identity_md(user_md)
        assert "田中太郎" in data["sections"]["基本情報"]

    def test_log_fixture_exists(self):
        assert (FIXTURES / "user_basic_info.md").exists()


class TestSoulFeedbackUpdate:
    """soul_feedback.md: トーン変更/結論ファースト/反論歓迎 → soul.md を更新。"""

    def test_detect_template_soul(self, tmp_path):
        soul_md = tmp_path / "soul.md"
        soul_md.write_text(
            "# Soul\n\n## コミュニケーションスタイル\n"
            "- トーン: [カジュアル / フォーマル / 等]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(soul_md)
        assert result["コミュニケーションスタイル"] is True

    def test_update_from_log(self, tmp_path):
        soul_md = tmp_path / "soul.md"
        soul_md.write_text(
            "# Soul\n\n## コミュニケーションスタイル\n"
            "- トーン: [カジュアル / フォーマル / 等]\n\n"
            "## 役割\n[このプロジェクトにおけるエージェントの役割を記述]\n",
            encoding="utf-8",
        )
        update_identity_section(
            soul_md, "コミュニケーションスタイル",
            "- トーン: カジュアル（敬語不要）\n- フォーマット: 結論ファースト",
        )
        update_identity_section(
            soul_md, "役割",
            "批判的思考パートナー（反論を歓迎される）",
        )
        result = detect_placeholder_sections(soul_md)
        assert result["コミュニケーションスタイル"] is False
        assert result["役割"] is False

    def test_log_fixture_exists(self):
        assert (FIXTURES / "soul_feedback.md").exists()


class TestAgentsProtocolUpdate:
    """agents_protocol.md: プロトコル変更要望 → agents.md 検知。"""

    def test_detect_template_agents(self, tmp_path):
        agents_md = tmp_path / "agents.md"
        agents_md.write_text(
            "# Agents\n\n## Live Logging\n[Configure your logging triggers here]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(agents_md)
        assert result["Live Logging"] is True

    def test_customized_not_placeholder(self, tmp_path):
        agents_md = tmp_path / "agents.md"
        agents_md.write_text(
            "# Agents\n\n## Live Logging\n"
            "重要な瞬間に memory/logs/YYYY-MM-DD.md に即座に追記する。\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(agents_md)
        assert result["Live Logging"] is False

    def test_log_fixture_exists(self):
        assert (FIXTURES / "agents_protocol.md").exists()


class TestNoIdentityUpdate:
    """no_identity_update.md: 技術的な作業のみ → 更新不要。"""

    def test_already_filled_stays_unchanged(self, tmp_path):
        user_md = tmp_path / "user.md"
        original = (
            "# ユーザープロファイル\n\n"
            "## 基本情報\n- 名前: Akira\n- 役割: コンサルタント\n\n"
            "## 専門性\nPython, SQL\n"
        )
        user_md.write_text(original, encoding="utf-8")
        result = detect_placeholder_sections(user_md)
        assert all(v is False for v in result.values())
        assert user_md.read_text(encoding="utf-8") == original

    def test_log_fixture_exists(self):
        assert (FIXTURES / "no_identity_update.md").exists()
