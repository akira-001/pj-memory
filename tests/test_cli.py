"""Tests for CLI commands: init, index, search."""

import json
from pathlib import Path

import pytest

from cognitive_memory.cli.main import main as cli_main


class TestInitCommand:
    def test_init_creates_scaffold(self, tmp_path):
        target = tmp_path / "my_project"
        target.mkdir()
        cli_main(["init", "--lang", "en", "--user-id", "tester", "--dir", str(target)])

        assert (target / "cogmem.toml").exists()
        assert (target / "memory" / "logs" / "tester" / ".gitkeep").exists()
        assert (target / ".gitignore").exists()

        # Verify .gitignore content
        gitignore = (target / ".gitignore").read_text()
        assert "*.db" in gitignore

    def test_init_existing_toml_preserved(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        toml_path = target / "cogmem.toml"
        toml_path.write_text("# existing config\n")

        cli_main(["init", "--lang", "en", "--user-id", "tester", "--dir", str(target)])

        # Original content should be preserved
        assert toml_path.read_text() == "# existing config\n"

    def test_init_updates_existing_gitignore(self, tmp_path):
        target = tmp_path / "with_gitignore"
        target.mkdir()
        gitignore = target / ".gitignore"
        gitignore.write_text("node_modules/\n")

        cli_main(["init", "--lang", "en", "--user-id", "tester", "--dir", str(target)])

        content = gitignore.read_text()
        assert "node_modules/" in content
        assert "*.db" in content

    def test_init_default_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cli_main(["init", "--lang", "en", "--user-id", "tester"])
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
        cli_main(["init", "--lang", "en", "--user-id", "tester"])

        # Create a sample log in user-specific directory
        log_file = tmp_path / "memory" / "logs" / "tester" / "2026-03-21.md"
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
        run_init(str(tmp_path), lang="en", user_id="tester")
        assert (tmp_path / "identity" / "agents.md").exists()
        assert (tmp_path / "identity" / "soul.md").exists()
        assert (tmp_path / "identity" / "user.md").exists()
        assert not (tmp_path / "identity" / "agent.md").exists()

    def test_init_creates_knowledge_dir(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="tester")
        assert (tmp_path / "memory" / "knowledge" / "summary.md").exists()
        assert (tmp_path / "memory" / "knowledge" / "error-patterns.md").exists()

    def test_init_creates_claude_md(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="tester")
        claude_md = tmp_path / "CLAUDE.md"
        assert claude_md.exists()
        assert "Cognitive Memory Agent" in claude_md.read_text()

    def test_init_appends_to_existing_claude_md(self, tmp_path):
        """Existing CLAUDE.md gets cogmem section appended."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# My Project\n\nExisting content.\n")
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="tester")
        content = claude_md.read_text()
        assert "My Project" in content
        assert "Cognitive Memory Agent" in content

    def test_init_skips_duplicate_claude_md(self, tmp_path):
        """Already has cogmem section -- does not duplicate."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Cognitive Memory Agent\n\nExisting cogmem.\n")
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="tester")
        content = claude_md.read_text()
        assert content.count("Cognitive Memory Agent") == 1

    def test_init_creates_contexts_dir(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="tester")
        assert (tmp_path / "memory" / "contexts" / "tester").is_dir()

    def test_init_ja_creates_japanese_templates(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="ja", user_id="tester")
        # soul.md should be in Japanese
        soul = (tmp_path / "identity" / "soul.md").read_text()
        assert "エージェント" in soul
        # agents.md should be in Japanese
        agents = (tmp_path / "identity" / "agents.md").read_text()
        assert "行動ルール" in agents
        # user.md should be in Japanese
        user = (tmp_path / "identity" / "user.md").read_text()
        assert "ユーザープロファイル" in user
        # CLAUDE.md should be in Japanese
        claude = (tmp_path / "CLAUDE.md").read_text()
        assert "行動ルール" in claude
        # knowledge files should be in Japanese
        summary = (tmp_path / "memory" / "knowledge" / "summary.md").read_text()
        assert "知識サマリー" in summary

    def test_init_ja_via_cli(self, tmp_path):
        target = tmp_path / "ja_project"
        target.mkdir()
        cli_main(["init", "--lang", "ja", "--user-id", "tester", "--dir", str(target)])
        soul = (target / "identity" / "soul.md").read_text()
        assert "エージェント" in soul

    def test_init_en_creates_english_templates(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="tester")
        soul = (tmp_path / "identity" / "soul.md").read_text()
        assert "Agent Identity" in soul


class TestMigrateCommand:
    """Tests for cogmem migrate."""

    def test_migrate_renames_agent_to_soul(self, tmp_path):
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agent.md").write_text("# Old Agent")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="tester")
        assert (identity / "soul.md").exists()
        assert not (identity / "agent.md").exists()
        assert (identity / "soul.md").read_text() == "# Old Agent"

    def test_migrate_creates_agents_md(self, tmp_path):
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="tester")
        agents_md = tmp_path / "identity" / "agents.md"
        assert agents_md.exists()
        assert "Session Init" in agents_md.read_text()

    def test_migrate_skips_existing_agents_md(self, tmp_path):
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agents.md").write_text("# Custom Rules")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="tester")
        assert (identity / "agents.md").read_text() == "# Custom Rules"

    def test_migrate_updates_toml(self, tmp_path):
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem.identity]\nagent = "identity/agent.md"\nuser = "identity/user.md"\n')
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="tester")
        content = toml.read_text()
        assert 'soul = "identity/soul.md"' in content
        assert "agent" not in content.split("user_id")[0]  # agent key removed (ignore user_id line)

    def test_migrate_adds_agents_ref_to_claude_md(self, tmp_path):
        claude = tmp_path / "CLAUDE.md"
        claude.write_text("# My Project\n\n@identity/soul.md\n@identity/user.md\n")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="tester")
        content = claude.read_text()
        assert "@identity/agents.md" in content
        assert "@identity/soul.md" in content

    def test_migrate_updates_claude_md(self, tmp_path):
        claude = tmp_path / "CLAUDE.md"
        claude.write_text("@identity/agent.md\n@identity/user.md\n")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="tester")
        content = claude.read_text()
        assert "@identity/soul.md" in content
        assert "@identity/agents.md" in content
        assert "@identity/agent.md" not in content

    def test_migrate_noop_when_up_to_date(self, tmp_path, capsys):
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agents.md").write_text("# Rules")
        (identity / "soul.md").write_text("# Soul")
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        # user_id already in local toml
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "existing"\n')
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="tester")
        assert "up to date" in capsys.readouterr().out

    def test_migrate_warns_both_exist(self, tmp_path, capsys):
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agent.md").write_text("# Old")
        (identity / "soul.md").write_text("# New")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="tester")
        assert "Both" in capsys.readouterr().err

    def test_migrate_via_cli(self, tmp_path):
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agent.md").write_text("# Agent")
        cli_main(["migrate", "--user-id", "tester", "--dir", str(tmp_path)])
        assert (identity / "soul.md").exists()
        assert (identity / "agents.md").exists()


class TestMigrateUserId:
    """Tests for user_id migration in cogmem migrate."""

    def test_migrate_writes_user_id_to_local_toml(self, tmp_path):
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        (tmp_path / "identity").mkdir()
        (tmp_path / "identity" / "agents.md").write_text("# Rules")
        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="alice")
        # user_id in cogmem.local.toml
        local_content = (tmp_path / "cogmem.local.toml").read_text()
        assert 'user_id = "alice"' in local_content
        # Not in cogmem.toml
        main_content = toml.read_text()
        assert 'user_id = "alice"' not in main_content

    def test_migrate_moves_logs_to_user_dir(self, tmp_path):
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        logs_dir = tmp_path / "memory" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "2026-03-20.md").write_text("# log 1")
        (logs_dir / "2026-03-21.md").write_text("# log 2")
        (logs_dir / "2026-03-19.compact.md").write_text("# compact")
        (tmp_path / "identity").mkdir()
        (tmp_path / "identity" / "agents.md").write_text("# Rules")

        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="alice")

        # Files moved to user subdirectory
        assert (logs_dir / "alice" / "2026-03-20.md").exists()
        assert (logs_dir / "alice" / "2026-03-21.md").exists()
        assert (logs_dir / "alice" / "2026-03-19.compact.md").exists()
        # Original files removed
        assert not (logs_dir / "2026-03-20.md").exists()
        assert not (logs_dir / "2026-03-21.md").exists()

    def test_migrate_moves_contexts_to_user_dir(self, tmp_path):
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        contexts_dir = tmp_path / "memory" / "contexts"
        contexts_dir.mkdir(parents=True)
        (contexts_dir / "2026-03-20.md").write_text("# context")
        (tmp_path / "identity").mkdir()
        (tmp_path / "identity" / "agents.md").write_text("# Rules")

        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="alice")

        assert (contexts_dir / "alice" / "2026-03-20.md").exists()
        assert not (contexts_dir / "2026-03-20.md").exists()

    def test_migrate_skips_if_local_toml_has_user_id(self, tmp_path, capsys):
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "bob"\n')
        (tmp_path / "identity").mkdir()
        (tmp_path / "identity" / "agents.md").write_text("# Rules")

        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="alice")

        # user_id should remain "bob" in local.toml
        local_content = (tmp_path / "cogmem.local.toml").read_text()
        assert 'user_id = "bob"' in local_content
        assert "up to date" in capsys.readouterr().out

    def test_migrate_moves_user_id_from_toml_to_local(self, tmp_path):
        """Old user_id in cogmem.toml is moved to cogmem.local.toml."""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nuser_id = "bob"\nlogs_dir = "memory/logs"\n')
        (tmp_path / "identity").mkdir()
        (tmp_path / "identity" / "agents.md").write_text("# Rules")

        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="bob")

        # user_id moved to local.toml
        local_content = (tmp_path / "cogmem.local.toml").read_text()
        assert 'user_id = "bob"' in local_content
        # Removed from cogmem.toml
        main_content = toml.read_text()
        assert "user_id" not in main_content

    def test_migrate_does_not_move_subdirectories(self, tmp_path):
        """Existing user subdirectories should not be moved."""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        logs_dir = tmp_path / "memory" / "logs"
        logs_dir.mkdir(parents=True)
        # File at root level (should be moved)
        (logs_dir / "2026-03-20.md").write_text("# log")
        # Existing subdirectory (should NOT be moved)
        (logs_dir / "other_user").mkdir()
        (logs_dir / "other_user" / "2026-03-20.md").write_text("# other")
        (tmp_path / "identity").mkdir()
        (tmp_path / "identity" / "agents.md").write_text("# Rules")

        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="alice")

        assert (logs_dir / "alice" / "2026-03-20.md").exists()
        # Other user's directory untouched
        assert (logs_dir / "other_user" / "2026-03-20.md").exists()

    def test_migrate_user_id_via_cli(self, tmp_path):
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        logs_dir = tmp_path / "memory" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "2026-03-20.md").write_text("# log")
        (tmp_path / "identity").mkdir()
        (tmp_path / "identity" / "agents.md").write_text("# Rules")

        cli_main(["migrate", "--user-id", "alice", "--dir", str(tmp_path)])

        assert 'user_id = "alice"' in (tmp_path / "cogmem.local.toml").read_text()
        assert (logs_dir / "alice" / "2026-03-20.md").exists()

    def test_migrate_copies_user_identity(self, tmp_path):
        """migrate copies identity/user.md → identity/users/{user_id}.md"""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agents.md").write_text("# Rules")
        (identity / "user.md").write_text("# Akira\nRole: Consultant\n")

        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="akira")

        per_user = identity / "users" / "akira.md"
        assert per_user.exists()
        assert "Consultant" in per_user.read_text()
        # Original user.md is preserved (shared template)
        assert (identity / "user.md").exists()

    def test_migrate_skips_existing_user_identity(self, tmp_path):
        """migrate does not overwrite existing per-user identity."""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        identity = tmp_path / "identity"
        identity.mkdir()
        (identity / "agents.md").write_text("# Rules")
        (identity / "user.md").write_text("# Template")
        users_dir = identity / "users"
        users_dir.mkdir()
        (users_dir / "akira.md").write_text("# Custom Akira Profile")

        from cognitive_memory.cli.migrate_cmd import run_migrate
        run_migrate(str(tmp_path), user_id="akira")

        # Existing file preserved
        assert (users_dir / "akira.md").read_text() == "# Custom Akira Profile"

    def test_migrate_prompt_rejects_taken_id(self, tmp_path, monkeypatch):
        """Interactive prompt rejects IDs with existing logs."""
        from cognitive_memory.cli.migrate_cmd import _prompt_user_id_for_migrate
        logs_dir = tmp_path / "memory" / "logs"
        (logs_dir / "bob").mkdir(parents=True)
        (logs_dir / "bob" / "2026-03-20.md").write_text("# log")

        inputs = iter(["bob", "alice"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        result = _prompt_user_id_for_migrate(logs_dir)
        assert result == "alice"


class TestSetupHooks:
    """Tests for cogmem init hooks auto-setup."""

    def test_init_creates_settings_json_hooks(self, tmp_path, monkeypatch):
        """cogmem init が .claude/settings.json に hooks を登録する"""
        monkeypatch.chdir(tmp_path)
        from cognitive_memory.cli.init_cmd import setup_hooks
        settings_dir = tmp_path / ".claude"
        setup_hooks(str(settings_dir))

        settings_file = settings_dir / "settings.json"
        assert settings_file.exists()
        import json
        settings = json.loads(settings_file.read_text())
        assert "hooks" in settings
        assert "PreToolUse" in settings["hooks"]
        assert "PostToolUse" in settings["hooks"]
        pre = settings["hooks"]["PreToolUse"][0]
        assert pre["matcher"] == "Edit|Write"
        assert pre["hooks"][0]["type"] == "command"
        assert "cogmem hook skill-gate" in pre["hooks"][0]["command"]

    def test_hooks_schema_validation_catches_old_format(self, tmp_path):
        """古い形式 { matcher, command } はバリデーションエラーになる"""
        from cognitive_memory.cli.init_cmd import _validate_hooks_schema
        import pytest

        bad_settings = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Edit|Write",
                    "command": "cogmem hook skill-gate",
                }]
            }
        }
        with pytest.raises(ValueError, match="missing 'hooks' array"):
            _validate_hooks_schema(bad_settings)

    def test_hooks_schema_validation_accepts_correct_format(self, tmp_path):
        """正しい形式はバリデーションを通過する"""
        from cognitive_memory.cli.init_cmd import _validate_hooks_schema

        good_settings = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Edit|Write",
                    "hooks": [{"type": "command", "command": "cogmem hook skill-gate"}],
                }]
            }
        }
        _validate_hooks_schema(good_settings)  # no error

    def test_init_merges_existing_settings_json(self, tmp_path, monkeypatch):
        """既存の settings.json がある場合はマージする"""
        monkeypatch.chdir(tmp_path)
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        settings_file = settings_dir / "settings.json"
        settings_file.write_text('{"existing_key": true}')

        from cognitive_memory.cli.init_cmd import setup_hooks
        setup_hooks(str(settings_dir))

        import json
        settings = json.loads(settings_file.read_text())
        assert settings["existing_key"] is True
        assert "hooks" in settings
