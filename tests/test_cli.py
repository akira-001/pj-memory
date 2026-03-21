"""Tests for CLI commands: init, index, search."""

import json
from pathlib import Path

import pytest

from cognitive_memory.cli.main import main as cli_main


class TestInitCommand:
    def test_init_creates_scaffold(self, tmp_path):
        target = tmp_path / "my_project"
        target.mkdir()
        cli_main(["init", "--dir", str(target)])

        assert (target / "cogmem.toml").exists()
        assert (target / "memory" / "logs" / ".gitkeep").exists()
        assert (target / ".gitignore").exists()

        # Verify .gitignore content
        gitignore = (target / ".gitignore").read_text()
        assert "*.db" in gitignore

    def test_init_existing_toml_preserved(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        toml_path = target / "cogmem.toml"
        toml_path.write_text("# existing config\n")

        cli_main(["init", "--dir", str(target)])

        # Original content should be preserved
        assert toml_path.read_text() == "# existing config\n"

    def test_init_updates_existing_gitignore(self, tmp_path):
        target = tmp_path / "with_gitignore"
        target.mkdir()
        gitignore = target / ".gitignore"
        gitignore.write_text("node_modules/\n")

        cli_main(["init", "--dir", str(target)])

        content = gitignore.read_text()
        assert "node_modules/" in content
        assert "*.db" in content

    def test_init_default_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli_main(["init"])
        assert (tmp_path / "cogmem.toml").exists()


class TestSearchCommand:
    def test_search_json_output(self, tmp_path, monkeypatch, capsys, mock_embedder):
        # Set up a minimal project
        monkeypatch.chdir(tmp_path)
        cli_main(["init"])

        # Create a sample log
        log_file = tmp_path / "memory" / "logs" / "2026-03-21.md"
        log_file.write_text("""# 2026-03-21 セッションログ

## ログエントリ

### [INSIGHT][TECH] テスト洞察エントリ
*Arousal: 0.7 | Emotion: Clarity*
これはCLIテスト用の洞察エントリ。十分な長さが必要。

---

## 引き継ぎ
- N/A
""")

        # Patch embedder to avoid Ollama dependency
        monkeypatch.setattr(
            "cognitive_memory.store.MemoryStore.embedder",
            property(lambda self: mock_embedder),
        )

        cli_main(["index"])

        # Clear captured output from init+index before search
        capsys.readouterr()

        cli_main(["search", "テスト洞察エントリの検索", "--json"])

        captured = capsys.readouterr()
        # Find the JSON line in output
        lines = [l for l in captured.out.strip().split("\n") if l.startswith("{")]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert "results" in data
        assert "status" in data
