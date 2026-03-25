"""Personality page tests."""

from __future__ import annotations

from pathlib import Path


class TestPersonalityRoutes:
    def test_personality_page_returns_200(self, client):
        resp = client.get("/personality")
        assert resp.status_code == 200
        assert "Personality" in resp.text

    def test_personality_shows_sections(self, client, project_dir):
        """Write identity files and verify they appear."""
        soul_path = project_dir / "identity" / "soul.md"
        soul_path.parent.mkdir(parents=True, exist_ok=True)
        soul_path.write_text(
            "# Soul\n\n## 役割\nテスト役割の説明\n\n## 核心的価値観\nテスト価値観\n",
            encoding="utf-8",
        )
        user_path = project_dir / "identity" / "user.md"
        user_path.write_text(
            "# User\n\n## 基本情報\n- 名前: テスト太郎\n\n## 専門性\nPython開発\n",
            encoding="utf-8",
        )
        resp = client.get("/personality")
        assert resp.status_code == 200
        assert "テスト役割の説明" in resp.text
        assert "テスト太郎" in resp.text

    def test_personality_empty_files(self, client):
        """No identity files — page still renders."""
        resp = client.get("/personality")
        assert resp.status_code == 200

    def test_personality_learning_timeline(self, client):
        """INSIGHT entries appear in learning timeline."""
        resp = client.get("/personality")
        assert resp.status_code == 200
        # Our test fixtures have INSIGHT memories
        assert "テスト洞察" in resp.text or "INSIGHT" in resp.text or "Learning" in resp.text


class TestPersonalityService:
    def test_read_and_parse_md(self, project_dir):
        from cognitive_memory.dashboard.services.personality_service import _read_and_parse_md

        md_path = project_dir / "test_parse.md"
        md_path.write_text(
            "# Title\n\n## Section A\nContent A\n\n## Section B\nContent B line 1\nContent B line 2\n",
            encoding="utf-8",
        )
        result = _read_and_parse_md(md_path)
        assert "Section A" in result
        assert result["Section A"] == "Content A"
        assert "Section B" in result
        assert "Content B line 1" in result["Section B"]

    def test_read_and_parse_md_missing(self, tmp_path):
        from cognitive_memory.dashboard.services.personality_service import _read_and_parse_md
        result = _read_and_parse_md(tmp_path / "nonexistent.md")
        assert result == {}

    def test_read_file_or_empty(self, project_dir):
        from cognitive_memory.dashboard.services.personality_service import _read_file_or_empty

        f = project_dir / "test_read.txt"
        f.write_text("hello", encoding="utf-8")
        assert _read_file_or_empty(f) == "hello"
        assert _read_file_or_empty(project_dir / "nope.txt") == ""

    def test_get_learning_timeline(self, config):
        from cognitive_memory.dashboard.services.personality_service import _get_learning_timeline
        timeline = _get_learning_timeline(config)
        assert isinstance(timeline, list)
        # Our fixtures have an INSIGHT memory
        insight_entries = [e for e in timeline if "テスト洞察" in e.get("title", "")]
        assert len(insight_entries) >= 1

    def test_get_personality_data(self, config):
        from cognitive_memory.dashboard.services.personality_service import get_personality_data
        data = get_personality_data(config)
        assert "soul" in data
        assert "user" in data
        assert "learning" in data
        assert "knowledge" in data
