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


    def test_init_missing_templates_raises(self, tmp_path, monkeypatch):
        """Raises RuntimeError when templates directory is missing."""
        import cognitive_memory.cli.init_cmd as init_mod
        monkeypatch.setattr(init_mod, "_SCAFFOLD_DIR", tmp_path / "nonexistent")
        with pytest.raises(RuntimeError, match="templates directory not found"):
            init_mod.run_init(str(tmp_path / "out"))


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
        data = json.loads(captured.out.strip())
        assert "results" in data
        assert "status" in data


class TestSignalsCli:
    """Tests for cogmem signals CLI."""

    def test_signals_no_logs(self, tmp_path, monkeypatch):
        """cogmem signals works with empty logs."""
        logs = tmp_path / "memory" / "logs"
        logs.mkdir(parents=True)
        toml = tmp_path / "cogmem.toml"
        toml.write_text(f'[cogmem]\nlogs_dir = "{logs}"\n')
        monkeypatch.setenv("COGMEM_CONFIG", str(toml))
        # Should not raise
        cli_main(["signals"])


class TestInitExtended:
    """Tests for extended cogmem init."""

    def test_init_creates_identity_dir(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path))
        assert (tmp_path / "identity" / "soul.md").exists()
        assert (tmp_path / "identity" / "user.md").exists()
        assert not (tmp_path / "identity" / "agent.md").exists()

    def test_init_creates_knowledge_dir(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path))
        assert (tmp_path / "memory" / "knowledge" / "summary.md").exists()
        assert (tmp_path / "memory" / "knowledge" / "error-patterns.md").exists()

    def test_init_creates_claude_md(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path))
        claude_md = tmp_path / "CLAUDE.md"
        assert claude_md.exists()
        assert "Cognitive Memory Agent" in claude_md.read_text()

    def test_init_appends_to_existing_claude_md(self, tmp_path):
        """Existing CLAUDE.md gets cogmem section appended."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# My Project\n\nExisting content.\n")
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path))
        content = claude_md.read_text()
        assert "My Project" in content
        assert "Cognitive Memory Agent" in content

    def test_init_skips_duplicate_claude_md(self, tmp_path):
        """Already has cogmem section -- does not duplicate."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Cognitive Memory Agent\n\nExisting cogmem.\n")
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path))
        content = claude_md.read_text()
        assert content.count("Cognitive Memory Agent") == 1

    def test_init_creates_contexts_dir(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path))
        assert (tmp_path / "memory" / "contexts").is_dir()


class TestMigrateCommand:
    """Tests for cogmem migrate."""

    def test_migrate_renames_agent_to_soul(self, tmp_path):
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agent.md").write_text("# Old Agent")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path))
        assert (identity / "soul.md").exists()
        assert not (identity / "agent.md").exists()
        assert (identity / "soul.md").read_text() == "# Old Agent"

    def test_migrate_updates_toml(self, tmp_path):
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem.identity]\nagent = "identity/agent.md"\nuser = "identity/user.md"\n')
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path))
        content = toml.read_text()
        assert 'soul = "identity/soul.md"' in content
        assert "agent" not in content

    def test_migrate_updates_claude_md(self, tmp_path):
        claude = tmp_path / "CLAUDE.md"
        claude.write_text("@identity/agent.md\n@identity/user.md\n")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path))
        content = claude.read_text()
        assert "@identity/soul.md" in content
        assert "@identity/agent.md" not in content

    def test_migrate_noop_when_up_to_date(self, tmp_path, capsys):
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path))
        assert "up to date" in capsys.readouterr().out

    def test_migrate_warns_both_exist(self, tmp_path, capsys):
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agent.md").write_text("# Old")
        (identity / "soul.md").write_text("# New")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path))
        assert "Both" in capsys.readouterr().err

    def test_migrate_via_cli(self, tmp_path):
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agent.md").write_text("# Agent")
        cli_main(["migrate", "--dir", str(tmp_path)])
        assert (identity / "soul.md").exists()
