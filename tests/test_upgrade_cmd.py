"""Tests for cogmem upgrade-check."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from cognitive_memory.cli import upgrade_cmd


def _write_toml(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


# ----- _parse_version -----

def test_parse_version_simple():
    assert upgrade_cmd._parse_version("0.24.0") == (0, 24, 0)
    assert upgrade_cmd._parse_version("1.0.0") == (1, 0, 0)
    assert upgrade_cmd._parse_version("0.25.1") == (0, 25, 1)


def test_parse_version_handles_pre_release_suffix():
    # 0.24.0a1 should still parse the numeric prefix
    assert upgrade_cmd._parse_version("0.24.0a1") == (0, 24, 0)
    assert upgrade_cmd._parse_version("1.2.3.dev0") == (1, 2, 3)


def test_parse_version_short_form():
    # 0.24 → (0, 24, 0)
    assert upgrade_cmd._parse_version("0.24") == (0, 24, 0)


def test_parse_version_ordering():
    assert upgrade_cmd._parse_version("0.25.0") > upgrade_cmd._parse_version("0.24.0")
    assert upgrade_cmd._parse_version("0.24.1") > upgrade_cmd._parse_version("0.24.0")
    assert upgrade_cmd._parse_version("1.0.0") > upgrade_cmd._parse_version("0.99.99")


# ----- _within_cache / _within_skip -----

def test_within_cache_recent_returns_true():
    recent = (datetime.now() - timedelta(hours=1)).isoformat()
    assert upgrade_cmd._within_cache(recent) is True


def test_within_cache_stale_returns_false():
    stale = (datetime.now() - timedelta(hours=25)).isoformat()
    assert upgrade_cmd._within_cache(stale) is False


def test_within_cache_empty_returns_false():
    assert upgrade_cmd._within_cache("") is False


def test_within_skip_future_date_returns_true():
    future = (date.today() + timedelta(days=3)).isoformat()
    assert upgrade_cmd._within_skip(future) is True


def test_within_skip_past_date_returns_false():
    past = (date.today() - timedelta(days=1)).isoformat()
    assert upgrade_cmd._within_skip(past) is False


# ----- run_upgrade_check -----

@pytest.fixture
def fake_pypi(monkeypatch):
    """Patch _fetch_latest_pypi to return a controlled latest version."""
    def _make(version: str = "0.99.0", release_date: str = "2026-04-26"):
        def _fake():
            return {
                "version": version,
                "summary": "Test summary",
                "release_date": release_date,
            }
        monkeypatch.setattr(upgrade_cmd, "_fetch_latest_pypi", _fake)
    return _make


def test_upgrade_available_when_pypi_newer(tmp_path, fake_pypi, capsys):
    fake_pypi(version="9.9.9")
    _write_toml(tmp_path / "cogmem.toml", '[cogmem]\nuser_id = "x"\n')
    result = upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=True, force=True)
    assert result["status"] == "upgrade_available"
    assert result["latest"] == "9.9.9"
    assert result["upgrade_command"] == "pip install -U cogmem-agent"
    assert result["post_install"] == "cogmem init"
    # last_check should be recorded
    cfg = upgrade_cmd._read_toml(tmp_path / "cogmem.toml")
    assert "last_check" in cfg.get("updates", {})


def test_up_to_date_when_pypi_same_or_older(tmp_path, fake_pypi):
    fake_pypi(version="0.0.1")  # older than current
    _write_toml(tmp_path / "cogmem.toml", '[cogmem]\nuser_id = "x"\n')
    result = upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=True, force=True)
    assert result["status"] == "up_to_date"


def test_skipped_when_auto_never(tmp_path, fake_pypi):
    fake_pypi(version="9.9.9")  # would be available
    _write_toml(tmp_path / "cogmem.toml", '[cogmem]\nuser_id = "x"\n[updates]\nauto = "never"\n')
    result = upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=True)
    assert result["status"] == "skipped"
    assert result["reason"] == "auto=never"


def test_skipped_when_skip_until_in_future(tmp_path, fake_pypi):
    fake_pypi(version="9.9.9")
    skip_until = (date.today() + timedelta(days=5)).isoformat()
    _write_toml(
        tmp_path / "cogmem.toml",
        f'[cogmem]\nuser_id = "x"\n[updates]\nskip_until = "{skip_until}"\n',
    )
    result = upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=True)
    assert result["status"] == "skipped"
    assert result["reason"].startswith("skip_until=")


def test_skipped_when_cached(tmp_path, fake_pypi):
    fake_pypi(version="9.9.9")
    last = datetime.now().isoformat(timespec="seconds")
    _write_toml(
        tmp_path / "cogmem.toml",
        f'[cogmem]\nuser_id = "x"\n[updates]\nlast_check = "{last}"\n',
    )
    result = upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=True)
    assert result["status"] == "skipped"
    assert result["reason"] == "cached"


def test_force_bypasses_cache(tmp_path, fake_pypi):
    fake_pypi(version="9.9.9")
    last = datetime.now().isoformat(timespec="seconds")
    _write_toml(
        tmp_path / "cogmem.toml",
        f'[cogmem]\nuser_id = "x"\n[updates]\nlast_check = "{last}"\n',
    )
    result = upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=True, force=True)
    assert result["status"] == "upgrade_available"


def test_pypi_unreachable_returns_error(tmp_path, monkeypatch):
    monkeypatch.setattr(upgrade_cmd, "_fetch_latest_pypi", lambda: None)
    _write_toml(tmp_path / "cogmem.toml", '[cogmem]\nuser_id = "x"\n')
    result = upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=True, force=True)
    assert result["status"] == "error"
    assert result["reason"] == "pypi_unreachable"


def test_json_output_emits_valid_json(tmp_path, fake_pypi, capsys):
    fake_pypi(version="9.9.9")
    _write_toml(tmp_path / "cogmem.toml", '[cogmem]\nuser_id = "x"\n')
    upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=True, force=True)
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["status"] == "upgrade_available"
    assert parsed["latest"] == "9.9.9"


def test_human_output_when_upgrade_available(tmp_path, fake_pypi, capsys):
    fake_pypi(version="9.9.9")
    _write_toml(tmp_path / "cogmem.toml", '[cogmem]\nuser_id = "x"\n')
    upgrade_cmd.run_upgrade_check(base_dir=tmp_path, json_output=False, force=True)
    out = capsys.readouterr().out
    assert "9.9.9" in out
    assert "pip install -U cogmem-agent" in out


# ----- mark_skip_until -----

def test_mark_skip_until_writes_section(tmp_path):
    _write_toml(tmp_path / "cogmem.toml", '[cogmem]\nuser_id = "x"\n')
    upgrade_cmd.mark_skip_until(tmp_path, days=7)
    cfg = upgrade_cmd._read_toml(tmp_path / "cogmem.toml")
    assert "updates" in cfg
    assert "skip_until" in cfg["updates"]
    expected = (date.today() + timedelta(days=7)).isoformat()
    assert cfg["updates"]["skip_until"] == expected


def test_mark_skip_until_preserves_other_sections(tmp_path):
    _write_toml(
        tmp_path / "cogmem.toml",
        '[cogmem]\nuser_id = "akira"\nlogs_dir = "memory/logs"\n',
    )
    upgrade_cmd.mark_skip_until(tmp_path, days=3)
    cfg = upgrade_cmd._read_toml(tmp_path / "cogmem.toml")
    assert cfg["cogmem"]["user_id"] == "akira"
    assert cfg["cogmem"]["logs_dir"] == "memory/logs"
    assert "skip_until" in cfg["updates"]


# ----- _write_updates_section idempotency -----

def test_write_updates_section_overwrites_existing(tmp_path):
    _write_toml(
        tmp_path / "cogmem.toml",
        '[cogmem]\nuser_id = "x"\n[updates]\nlast_check = "2020-01-01T00:00:00"\n',
    )
    upgrade_cmd._write_updates_section(
        tmp_path / "cogmem.toml",
        {"last_check": "2026-04-26T12:00:00"},
    )
    cfg = upgrade_cmd._read_toml(tmp_path / "cogmem.toml")
    assert cfg["updates"]["last_check"] == "2026-04-26T12:00:00"
    # Other section preserved
    assert cfg["cogmem"]["user_id"] == "x"
