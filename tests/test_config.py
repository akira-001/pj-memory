"""Tests for config module: TOML loading, find_and_load, defaults."""

import os
import tempfile
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig


class TestDefaults:
    def test_default_config(self):
        cfg = CogMemConfig()
        assert cfg.logs_dir == "memory/logs"
        assert cfg.db_path == "memory/vectors.db"
        assert cfg.sim_weight == 0.7
        assert cfg.arousal_weight == 0.3
        assert cfg.base_half_life == 60.0
        assert cfg.decay_floor == 0.3
        assert cfg.embedding_provider == "ollama"
        assert cfg.embedding_timeout == 10


class TestFromToml:
    def test_load_full_config(self, tmp_path):
        toml_content = """
[cogmem]
logs_dir = "custom/logs"
db_path = "custom/db.sqlite"
handover_delimiter = "## Handover"

[cogmem.scoring]
sim_weight = 0.8
arousal_weight = 0.2
base_half_life = 45.0
decay_floor = 0.2

[cogmem.embedding]
provider = "openai"
model = "text-embedding-3-small"
url = "https://api.openai.com/v1/embeddings"
timeout = 30
"""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text(toml_content)

        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.logs_dir == "custom/logs"
        assert cfg.db_path == "custom/db.sqlite"
        assert cfg.handover_delimiter == "## Handover"
        assert cfg.sim_weight == 0.8
        assert cfg.arousal_weight == 0.2
        assert cfg.base_half_life == 45.0
        assert cfg.decay_floor == 0.2
        assert cfg.embedding_provider == "openai"
        assert cfg.embedding_timeout == 30

    def test_partial_config_uses_defaults(self, tmp_path):
        toml_content = """
[cogmem]
logs_dir = "my/logs"
"""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text(toml_content)

        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.logs_dir == "my/logs"
        assert cfg.db_path == "memory/vectors.db"  # default
        assert cfg.sim_weight == 0.7  # default

    def test_empty_toml(self, tmp_path):
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("")
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.logs_dir == "memory/logs"

    def test_base_dir_set_to_parent(self, tmp_path):
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg._base_dir == str(tmp_path)

    def test_logs_path_resolved(self, tmp_path):
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.logs_path == tmp_path / "memory" / "logs"
        assert cfg.database_path == tmp_path / "memory" / "vectors.db"


class TestFindAndLoad:
    def test_find_in_current_dir(self, tmp_path):
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text('[cogmem]\nlogs_dir = "found"\n')
        cfg = CogMemConfig.find_and_load(start_dir=tmp_path)
        assert cfg.logs_dir == "found"

    def test_find_in_parent_dir(self, tmp_path):
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text('[cogmem]\nlogs_dir = "parent_found"\n')
        child = tmp_path / "sub" / "deep"
        child.mkdir(parents=True)
        cfg = CogMemConfig.find_and_load(start_dir=child)
        assert cfg.logs_dir == "parent_found"

    def test_fallback_to_defaults(self, tmp_path):
        # No cogmem.toml anywhere in tmp_path hierarchy
        child = tmp_path / "empty" / "project"
        child.mkdir(parents=True)
        cfg = CogMemConfig.find_and_load(start_dir=child)
        assert cfg.logs_dir == "memory/logs"

    def test_env_var_override(self, tmp_path, monkeypatch):
        toml_file = tmp_path / "env_config.toml"
        toml_file.write_text('[cogmem]\nlogs_dir = "from_env"\n')
        monkeypatch.setenv("COGMEM_CONFIG", str(toml_file))
        cfg = CogMemConfig.find_and_load(start_dir=tmp_path)
        assert cfg.logs_dir == "from_env"


class TestConfigNewSections:
    """Tests for v0.2.0 config extensions."""

    def test_parse_identity_section(self, tmp_path):
        """New [cogmem.identity] section is parsed."""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem.identity]\nsoul = "custom/soul.md"\nuser = "custom/user.md"\n')
        config = CogMemConfig.from_toml(toml)
        assert config.identity_soul == "custom/soul.md"
        assert config.identity_user == "custom/user.md"

    def test_backward_compat_agent_key(self, tmp_path, capsys):
        """Old agent= key is accepted with deprecation warning."""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem.identity]\nagent = "identity/agent.md"\n')
        config = CogMemConfig.from_toml(toml)
        assert config.identity_soul == "identity/agent.md"
        assert "deprecated" in capsys.readouterr().err.lower()

    def test_parse_crystallization_section(self, tmp_path):
        """New [cogmem.crystallization] section is parsed."""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem.crystallization]\npattern_threshold = 5\nerror_threshold = 10\nlast_checkpoint = "2026-03-15"\n')
        config = CogMemConfig.from_toml(toml)
        assert config.pattern_threshold == 5
        assert config.error_threshold == 10
        assert config.last_checkpoint == "2026-03-15"

    def test_missing_new_sections_use_defaults(self, tmp_path):
        """Missing new sections fall back to defaults (backward compat)."""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\nlogs_dir = "logs"\n')
        config = CogMemConfig.from_toml(toml)
        assert config.identity_soul == "identity/soul.md"
        assert config.pattern_threshold == 3
        assert config.total_sessions == 0

    def test_path_properties(self, tmp_path):
        """New path properties resolve relative to base dir."""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('[cogmem]\n')
        config = CogMemConfig.from_toml(toml)
        assert config.identity_soul_path == tmp_path / "identity" / "soul.md"
        assert config.knowledge_summary_path == tmp_path / "memory" / "knowledge" / "summary.md"
        assert config.contexts_path == tmp_path / "memory" / "contexts"


class TestContextSearchConfig:
    def test_defaults(self):
        """Default context_search values are correct."""
        cfg = CogMemConfig()
        assert cfg.context_search_enabled is True
        assert cfg.context_flashback_sim == 0.65
        assert cfg.context_flashback_arousal == 0.5
        assert cfg.context_cache_max_size == 20
        assert cfg.context_cache_sim_threshold == 0.9

    def test_from_toml_context_search(self, tmp_path):
        """TOML [cogmem.context_search] section is parsed."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text(
            """
[cogmem.context_search]
enabled = false
flashback_sim = 0.7
flashback_arousal = 0.6
cache_max_size = 10
cache_sim_threshold = 0.95
"""
        )
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.context_search_enabled is False
        assert cfg.context_flashback_sim == 0.7
        assert cfg.context_flashback_arousal == 0.6
        assert cfg.context_cache_max_size == 10
        assert cfg.context_cache_sim_threshold == 0.95

    def test_missing_context_search_uses_defaults(self, tmp_path):
        """Missing [cogmem.context_search] falls back to defaults."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.context_search_enabled is True
        assert cfg.context_flashback_sim == 0.65


class TestUserIdIsolation:
    """Tests for per-user log isolation via user_id."""

    def test_default_user_id_empty_for_programmatic_use(self):
        """Direct CogMemConfig() has empty user_id (no path modification)."""
        cfg = CogMemConfig()
        assert cfg.user_id == ""

    def test_from_toml_without_user_id_is_empty(self, tmp_path):
        """from_toml without user_id leaves it empty (no path modification)."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.user_id == ""
        assert cfg.logs_path == tmp_path / "memory" / "logs"

    def test_find_and_load_warns_when_no_user_id(self, tmp_path, capsys):
        """find_and_load warns when user_id is not set in TOML."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        cfg = CogMemConfig.find_and_load(start_dir=tmp_path)
        assert cfg.user_id == ""
        assert cfg.logs_path == tmp_path / "memory" / "logs"
        captured = capsys.readouterr().err
        assert "user_id is not set" in captured
        assert "cogmem migrate" in captured

    def test_logs_path_with_user_id_in_local_toml(self, tmp_path):
        """user_id in cogmem.local.toml is picked up."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "akira"\n')
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.logs_path == tmp_path / "memory" / "logs" / "akira"

    def test_contexts_path_with_user_id(self, tmp_path):
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "akira"\n')
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.contexts_path == tmp_path / "memory" / "contexts" / "akira"

    def test_user_id_from_local_toml(self, tmp_path):
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "bob"\n')
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.user_id == "bob"

    def test_local_toml_overrides_main_toml(self, tmp_path):
        """cogmem.local.toml takes precedence over cogmem.toml."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text('[cogmem]\nuser_id = "old_user"\n')
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "local_user"\n')
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.user_id == "local_user"

    def test_db_path_not_affected_by_user_id(self, tmp_path):
        """DB is shared across users (search across users is useful)."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "akira"\n')
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.database_path == tmp_path / "memory" / "vectors.db"

    def test_identity_user_path_with_user_id(self, tmp_path):
        """user_id set + per-user file exists → identity/users/{user_id}.md"""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "alice"\n')
        per_user = tmp_path / "identity" / "users" / "alice.md"
        per_user.parent.mkdir(parents=True, exist_ok=True)
        per_user.write_text("# Alice\n")
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.identity_user_path == tmp_path / "identity" / "users" / "alice.md"

    def test_identity_user_path_with_user_id_fallback(self, tmp_path):
        """user_id set but per-user file missing → fallback to identity/user.md"""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "alice"\n')
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.identity_user_path == tmp_path / "identity" / "user.md"

    def test_identity_user_path_without_user_id(self, tmp_path):
        """No user_id → default identity/user.md"""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.identity_user_path == tmp_path / "identity" / "user.md"

    def test_identity_soul_path_not_affected_by_user_id(self, tmp_path):
        """Soul identity is shared across users."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        (tmp_path / "cogmem.local.toml").write_text('[cogmem]\nuser_id = "alice"\n')
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.identity_soul_path == tmp_path / "identity" / "soul.md"

    def test_no_local_toml_still_works(self, tmp_path):
        """Missing cogmem.local.toml does not break loading."""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text("[cogmem]\n")
        cfg = CogMemConfig.from_toml(toml_file)
        assert cfg.user_id == ""


class TestInitUserIdIsolation:
    """Tests for user_id handling in cogmem init."""

    def test_init_creates_user_specific_logs_dir(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="alice")
        assert (tmp_path / "memory" / "logs" / "alice" / ".gitkeep").exists()
        assert (tmp_path / "memory" / "contexts" / "alice" / ".gitkeep").exists()

    def test_init_creates_per_user_identity(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="alice")
        assert (tmp_path / "identity" / "users" / "alice.md").exists()
        # Shared user.md template also created
        assert (tmp_path / "identity" / "user.md").exists()

    def test_init_writes_user_id_to_local_toml(self, tmp_path):
        from cognitive_memory.cli.init_cmd import run_init
        run_init(str(tmp_path), lang="en", user_id="alice")
        # user_id should be in cogmem.local.toml, not cogmem.toml
        local_content = (tmp_path / "cogmem.local.toml").read_text()
        assert 'user_id = "alice"' in local_content
        main_content = (tmp_path / "cogmem.toml").read_text()
        assert 'user_id = "alice"' not in main_content

    def test_get_existing_user_ids(self, tmp_path):
        from cognitive_memory.cli.init_cmd import _get_existing_user_ids
        logs_dir = tmp_path / "memory" / "logs"
        # Create user dirs with logs
        (logs_dir / "alice").mkdir(parents=True)
        (logs_dir / "alice" / "2026-01-01.md").write_text("# log")
        (logs_dir / "bob").mkdir(parents=True)
        (logs_dir / "bob" / "2026-01-01.md").write_text("# log")
        # Empty dir should not count
        (logs_dir / "empty").mkdir(parents=True)

        ids = _get_existing_user_ids(logs_dir)
        assert ids == {"alice", "bob"}

    def test_get_existing_user_ids_no_dir(self, tmp_path):
        from cognitive_memory.cli.init_cmd import _get_existing_user_ids
        ids = _get_existing_user_ids(tmp_path / "nonexistent")
        assert ids == set()

    def test_prompt_rejects_taken_id(self, tmp_path, monkeypatch):
        """_prompt_user_id rejects IDs with existing logs."""
        from cognitive_memory.cli.init_cmd import _prompt_user_id
        logs_dir = tmp_path / "memory" / "logs"
        (logs_dir / "alice").mkdir(parents=True)
        (logs_dir / "alice" / "2026-01-01.md").write_text("# log")

        # First input "alice" (taken), then "carol" (available)
        inputs = iter(["alice", "carol"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        msg = {
            "user_id_prompt": "Enter user ID (default: {}): ",
            "user_id_taken": "ID '{}' taken ({})",
        }
        result = _prompt_user_id(logs_dir, msg)
        assert result == "carol"

    def test_prompt_rejects_invalid_chars(self, tmp_path, monkeypatch):
        """_prompt_user_id rejects IDs with special characters."""
        from cognitive_memory.cli.init_cmd import _prompt_user_id

        inputs = iter(["a b c", "../evil", "good-id"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        msg = {
            "user_id_prompt": "Enter user ID (default: {}): ",
            "user_id_taken": "ID '{}' taken ({})",
        }
        result = _prompt_user_id(tmp_path, msg)
        assert result == "good-id"


class TestBehaviorConfig:
    """Tests for [cogmem.behavior] and [[cogmem.skill_triggers]] config."""

    def test_behavior_defaults(self, tmp_path):
        """behavior セクション未定義でもデフォルト値が設定される"""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text('[cogmem]\nlogs_dir = "memory/logs"\n')
        config = CogMemConfig.from_toml(toml_file)
        assert config.consecutive_failure_threshold == 2
        assert config.skill_triggers == []
        assert config.skill_gate_enabled is True

    def test_behavior_from_toml(self, tmp_path):
        """behavior セクションが正しく読み込まれる"""
        toml_file = tmp_path / "cogmem.toml"
        toml_file.write_text('''[cogmem]
logs_dir = "memory/logs"

[cogmem.behavior]
consecutive_failure_threshold = 3
skill_gate = false

[[cogmem.skill_triggers]]
pattern = "src/dashboard/**"
skills = ["tdd-dashboard-dev"]

[[cogmem.skill_triggers]]
pattern = "cron-jobs.json"
skills = ["cron-automation"]
''')
        config = CogMemConfig.from_toml(toml_file)
        assert config.consecutive_failure_threshold == 3
        assert config.skill_gate_enabled is False
        assert len(config.skill_triggers) == 2
        assert config.skill_triggers[0]["pattern"] == "src/dashboard/**"
        assert config.skill_triggers[0]["skills"] == ["tdd-dashboard-dev"]
