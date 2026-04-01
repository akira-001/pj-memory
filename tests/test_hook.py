"""Tests for cogmem hook subcommands."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cognitive_memory.cli.hook_cmd import run_failure_breaker


class TestFailureBreaker:
    @pytest.fixture(autouse=True)
    def setup_state_dir(self, tmp_path):
        """一時ディレクトリを状態管理用に使う"""
        self.state_file = tmp_path / "cogmem-failure-count"
        with patch.dict(os.environ, {"COGMEM_HOOK_STATE": str(self.state_file)}):
            yield

    def test_first_failure_no_warning(self, tmp_path, capsys):
        """1回目の失敗では警告しない（閾値=2）"""
        hook_input = {"tool_name": "Bash", "tool_result": {"exit_code": 1}}
        with patch.dict(os.environ, {"COGMEM_HOOK_STATE": str(self.state_file)}):
            run_failure_breaker(hook_input, threshold=2)
        assert capsys.readouterr().err == ""

    def test_consecutive_failures_warns(self, tmp_path, capsys):
        """閾値到達で stderr に警告を出力"""
        hook_input = {"tool_name": "Bash", "tool_result": {"exit_code": 1}}
        with patch.dict(os.environ, {"COGMEM_HOOK_STATE": str(self.state_file)}):
            run_failure_breaker(hook_input, threshold=2)
            run_failure_breaker(hook_input, threshold=2)
        err = capsys.readouterr().err
        assert "2回連続で失敗" in err
        assert "根本原因" in err

    def test_success_resets_counter(self, tmp_path, capsys):
        """成功でカウンタリセット"""
        fail_input = {"tool_name": "Bash", "tool_result": {"exit_code": 1}}
        ok_input = {"tool_name": "Bash", "tool_result": {"exit_code": 0}}
        with patch.dict(os.environ, {"COGMEM_HOOK_STATE": str(self.state_file)}):
            run_failure_breaker(fail_input, threshold=2)
            run_failure_breaker(ok_input, threshold=2)
            run_failure_breaker(fail_input, threshold=2)
        assert capsys.readouterr().err == ""

    def test_warns_every_threshold(self, tmp_path, capsys):
        """閾値の倍数でも警告が出る"""
        hook_input = {"tool_name": "Bash", "tool_result": {"exit_code": 1}}
        with patch.dict(os.environ, {"COGMEM_HOOK_STATE": str(self.state_file)}):
            for _ in range(4):
                run_failure_breaker(hook_input, threshold=2)
        err = capsys.readouterr().err
        assert err.count("連続で失敗") == 2  # 2回目と4回目


class TestSkillGate:
    @pytest.fixture
    def config_dir(self, tmp_path):
        """cogmem.toml + skills.db がある一時ディレクトリ"""
        toml = tmp_path / "cogmem.toml"
        toml.write_text('''[cogmem]
logs_dir = "memory/logs"
user_id = "test"

[[cogmem.skill_triggers]]
pattern = "dashboard/templates/**"
skills = ["tdd-dashboard-dev"]
''')
        (tmp_path / "memory").mkdir()
        return tmp_path

    def test_warns_when_skill_not_used(self, config_dir, capsys, monkeypatch):
        """スキル未使用時に警告が出る"""
        monkeypatch.chdir(config_dir)
        hook_input = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(config_dir / "dashboard/templates/list.html")},
        }
        from cognitive_memory.cli.hook_cmd import run_skill_gate
        run_skill_gate(hook_input, base_dir=str(config_dir))
        err = capsys.readouterr().err
        assert "tdd-dashboard-dev" in err
        assert "未使用" in err

    def test_no_warn_when_skill_used(self, config_dir, capsys, monkeypatch):
        """skill_start 記録済みなら警告なし"""
        monkeypatch.chdir(config_dir)
        from cognitive_memory.config import CogMemConfig
        from cognitive_memory.skills.store import SkillsStore
        config = CogMemConfig.from_toml(config_dir / "cogmem.toml")
        store = SkillsStore(config)
        store.add_session_event(
            skill_name="tdd-dashboard-dev",
            event_type="skill_start",
            description="test",
        )
        hook_input = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(config_dir / "dashboard/templates/list.html")},
        }
        from cognitive_memory.cli.hook_cmd import run_skill_gate
        run_skill_gate(hook_input, base_dir=str(config_dir))
        assert capsys.readouterr().err == ""

    def test_no_warn_for_unmatched_file(self, config_dir, capsys, monkeypatch):
        """マッチしないファイルでは警告なし"""
        monkeypatch.chdir(config_dir)
        hook_input = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(config_dir / "src/main.py")},
        }
        from cognitive_memory.cli.hook_cmd import run_skill_gate
        run_skill_gate(hook_input, base_dir=str(config_dir))
        assert capsys.readouterr().err == ""


class TestHookEndToEnd:
    def test_failure_breaker_via_cli(self, tmp_path):
        """CLI 経由で failure-breaker が動作する"""
        import subprocess
        hook_input = json.dumps({
            "tool_name": "Bash",
            "tool_result": {"exit_code": 1},
        })
        env = os.environ.copy()
        env["COGMEM_HOOK_STATE"] = str(tmp_path / "state")

        # 1回目: 警告なし
        r1 = subprocess.run(
            ["cogmem", "hook", "failure-breaker"],
            input=hook_input, capture_output=True, text=True, env=env,
        )
        assert r1.returncode == 0
        assert r1.stderr == ""

        # 2回目: 警告あり
        r2 = subprocess.run(
            ["cogmem", "hook", "failure-breaker"],
            input=hook_input, capture_output=True, text=True, env=env,
        )
        assert r2.returncode == 0
        assert "連続で失敗" in r2.stderr
