"""Tests for decay settings UI on consolidation dashboard page."""

from __future__ import annotations

import pytest

from cognitive_memory.dashboard.services.consolidation_service import (
    get_decay_settings,
    save_decay_settings,
)


class TestGetDecaySettings:
    """Unit tests for get_decay_settings."""

    def test_default_values(self, crystal_rich_config):
        settings = get_decay_settings(crystal_rich_config)
        assert settings["arousal_threshold"] == 0.7
        assert settings["recall_threshold"] == 2
        assert settings["recall_window_months"] == 18
        assert settings["enabled"] is True

    def test_custom_values(self, crystal_rich_config):
        crystal_rich_config.decay_arousal_threshold = 0.5
        crystal_rich_config.decay_recall_threshold = 5
        crystal_rich_config.decay_recall_window_months = 6
        crystal_rich_config.decay_enabled = False
        settings = get_decay_settings(crystal_rich_config)
        assert settings["arousal_threshold"] == 0.5
        assert settings["recall_threshold"] == 5
        assert settings["recall_window_months"] == 6
        assert settings["enabled"] is False


class TestSaveDecaySettings:
    """Unit tests for save_decay_settings."""

    def test_creates_decay_section(self, crystal_rich_config, crystal_rich_dir):
        """When [cogmem.decay] doesn't exist, it should be appended."""
        toml_path = crystal_rich_dir / "cogmem.toml"
        save_decay_settings(crystal_rich_config, {
            "arousal_threshold": 0.5,
            "recall_threshold": 3,
            "recall_window_months": 12,
            "enabled": False,
        })
        content = toml_path.read_text(encoding="utf-8")
        assert "[cogmem.decay]" in content
        assert "arousal_threshold = 0.5" in content
        assert "recall_threshold = 3" in content
        assert "recall_window_months = 12" in content
        assert "enabled = false" in content

    def test_updates_existing_decay_section(self, tmp_path):
        """When [cogmem.decay] already exists, values should be updated."""
        from cognitive_memory.config import CogMemConfig

        toml_content = """\
[cogmem]
logs_dir = "memory/logs"
db_path = "memory/vectors.db"

[cogmem.decay]
arousal_threshold = 0.7
recall_threshold = 2
recall_window_months = 18
enabled = true
"""
        toml_path = tmp_path / "cogmem.toml"
        toml_path.write_text(toml_content, encoding="utf-8")

        # Create minimal dirs so config loads
        (tmp_path / "memory" / "logs").mkdir(parents=True)
        db_path = tmp_path / "memory" / "vectors.db"
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS indexed_files (filename TEXT PRIMARY KEY)")
        conn.close()

        config = CogMemConfig.from_toml(toml_path)
        save_decay_settings(config, {
            "arousal_threshold": 0.9,
            "recall_threshold": 5,
            "recall_window_months": 6,
            "enabled": False,
        })
        content = toml_path.read_text(encoding="utf-8")
        assert "arousal_threshold = 0.9" in content
        assert "recall_threshold = 5" in content
        assert "recall_window_months = 6" in content
        assert "enabled = false" in content
        # Old values should be gone
        assert "arousal_threshold = 0.7" not in content
        assert "recall_window_months = 18" not in content


class TestDecaySettingsRoute:
    """HTTP route tests for decay settings on consolidation page."""

    def test_get_shows_decay_form(self, crystal_rich_client):
        resp = crystal_rich_client.get("/consolidation")
        assert resp.status_code == 200
        html = resp.text
        # Form exists with decay fields
        assert 'name="arousal_threshold"' in html
        assert 'name="recall_threshold"' in html
        assert 'name="recall_window_months"' in html
        assert 'name="enabled"' in html

    def test_get_shows_default_values(self, crystal_rich_client):
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        # Default values in inputs
        assert 'value="0.7"' in html  # arousal_threshold
        assert 'value="2"' in html  # recall_threshold
        assert 'value="18"' in html  # recall_window_months

    def test_get_shows_decay_title_en(self, crystal_rich_client):
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        assert "Memory Decay Settings" in html

    def test_get_shows_decay_title_ja(self, crystal_rich_client):
        crystal_rich_client.cookies.set("lang", "ja")
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        assert "記憶の忘却設定" in html

    def test_post_updates_settings(self, crystal_rich_client, crystal_rich_config):
        resp = crystal_rich_client.post(
            "/consolidation/decay",
            data={
                "arousal_threshold": "0.5",
                "recall_threshold": "3",
                "recall_window_months": "12",
                "enabled": "on",
            },
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        # Verify in-memory config was updated
        assert crystal_rich_config.decay_arousal_threshold == 0.5
        assert crystal_rich_config.decay_recall_threshold == 3
        assert crystal_rich_config.decay_recall_window_months == 12
        assert crystal_rich_config.decay_enabled is True

    def test_post_disabled_checkbox(self, crystal_rich_client, crystal_rich_config):
        """When checkbox is unchecked, 'enabled' is not in form data."""
        resp = crystal_rich_client.post(
            "/consolidation/decay",
            data={
                "arousal_threshold": "0.7",
                "recall_threshold": "2",
                "recall_window_months": "18",
                # no "enabled" key = unchecked
            },
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert crystal_rich_config.decay_enabled is False

    def test_post_saves_to_toml(self, crystal_rich_client, crystal_rich_dir):
        crystal_rich_client.post(
            "/consolidation/decay",
            data={
                "arousal_threshold": "0.6",
                "recall_threshold": "4",
                "recall_window_months": "9",
            },
            follow_redirects=False,
        )
        content = (crystal_rich_dir / "cogmem.toml").read_text(encoding="utf-8")
        assert "arousal_threshold = 0.6" in content
        assert "recall_threshold = 4" in content
        assert "recall_window_months = 9" in content

    def test_values_reflected_after_save(self, crystal_rich_client):
        crystal_rich_client.post(
            "/consolidation/decay",
            data={
                "arousal_threshold": "0.9",
                "recall_threshold": "10",
                "recall_window_months": "3",
                "enabled": "on",
            },
            follow_redirects=True,
        )
        resp = crystal_rich_client.get("/consolidation")
        html = resp.text
        assert 'value="0.9"' in html
        assert 'value="10"' in html
        assert 'value="3"' in html
