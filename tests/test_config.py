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
