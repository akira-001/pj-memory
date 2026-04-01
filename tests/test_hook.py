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
