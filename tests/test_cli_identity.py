"""Identity CLI command tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cognitive_memory.cli.identity_cmd import run_identity_update, run_identity_show


class TestIdentityUpdate:
    def test_update_single_section(self, tmp_path):
        user_md = tmp_path / "identity" / "user.md"
        user_md.parent.mkdir(parents=True, exist_ok=True)
        user_md.write_text("# User\n\n## 基本情報\n- 名前:\n", encoding="utf-8")

        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = user_md
            run_identity_update(
                target="user", section="基本情報",
                content="- 名前: Akira\n- 役割: コンサルタント",
                json_input=None,
            )

        text = user_md.read_text(encoding="utf-8")
        assert "Akira" in text
        assert "コンサルタント" in text

    def test_update_json_multiple_sections(self, tmp_path):
        user_md = tmp_path / "identity" / "user.md"
        user_md.parent.mkdir(parents=True, exist_ok=True)
        user_md.write_text("# User\n\n## 基本情報\n- 名前:\n", encoding="utf-8")

        sections = {"基本情報": "- 名前: Akira", "専門性": "Python, Go"}
        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = user_md
            run_identity_update(
                target="user", section=None,
                content=None,
                json_input=json.dumps(sections),
            )

        text = user_md.read_text(encoding="utf-8")
        assert "Akira" in text
        assert "Python, Go" in text

    def test_update_soul(self, tmp_path):
        soul_md = tmp_path / "identity" / "soul.md"
        soul_md.parent.mkdir(parents=True, exist_ok=True)
        soul_md.write_text("# Soul\n\n## 役割\nテンプレート\n", encoding="utf-8")

        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_soul_path = soul_md
            run_identity_update(
                target="soul", section="役割",
                content="開発パートナー",
                json_input=None,
            )

        text = soul_md.read_text(encoding="utf-8")
        assert "開発パートナー" in text

    def test_update_invalid_json(self, tmp_path):
        """Invalid JSON should exit with error."""
        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = tmp_path / "user.md"
            with pytest.raises(SystemExit):
                run_identity_update(
                    target="user", section=None,
                    content=None,
                    json_input="not valid json",
                )

    def test_update_no_section_no_json(self, tmp_path):
        """Neither --section nor --json should exit with error."""
        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = tmp_path / "user.md"
            with pytest.raises(SystemExit):
                run_identity_update(
                    target="user", section=None,
                    content=None,
                    json_input=None,
                )


class TestIdentityShow:
    def test_show_user(self, tmp_path, capsys):
        user_md = tmp_path / "identity" / "user.md"
        user_md.parent.mkdir(parents=True, exist_ok=True)
        user_md.write_text("# User\n\n## 基本情報\n- 名前: Akira\n", encoding="utf-8")

        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = user_md
            mock.find_and_load.return_value.identity_soul_path = tmp_path / "nope.md"
            run_identity_show(target="user")

        out = capsys.readouterr().out
        assert "Akira" in out

    def test_show_both(self, tmp_path, capsys):
        user_md = tmp_path / "identity" / "user.md"
        soul_md = tmp_path / "identity" / "soul.md"
        user_md.parent.mkdir(parents=True, exist_ok=True)
        user_md.write_text("# User\n\n## 基本情報\n- 名前: Test\n", encoding="utf-8")
        soul_md.write_text("# Soul\n\n## 役割\nパートナー\n", encoding="utf-8")

        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = user_md
            mock.find_and_load.return_value.identity_soul_path = soul_md
            run_identity_show(target=None)

        out = capsys.readouterr().out
        assert "Test" in out
        assert "パートナー" in out

    def test_show_empty(self, tmp_path, capsys):
        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = tmp_path / "nope.md"
            mock.find_and_load.return_value.identity_soul_path = tmp_path / "nope2.md"
            run_identity_show(target=None)

        out = capsys.readouterr().out
        assert "(empty)" in out
