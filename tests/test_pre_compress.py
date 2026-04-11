"""Tests for cogmem hook pre-compress."""
from datetime import date
from pathlib import Path

import pytest

from cognitive_memory.cli.hook_cmd import run_pre_compress


@pytest.fixture
def logs_dir(tmp_path):
    d = tmp_path / "memory" / "logs"
    d.mkdir(parents=True)
    return d


def _hook_input(prompt: str, tool_name: str = "Task") -> dict:
    return {
        "tool_name": tool_name,
        "tool_input": {"prompt": prompt},
    }


class TestPreCompress:
    def test_non_task_tool_is_ignored(self, logs_dir):
        hook_input = _hook_input("do something", tool_name="Bash")
        result = run_pre_compress(hook_input, logs_dir=str(logs_dir))
        assert result is None

    def test_short_prompt_is_ignored(self, logs_dir):
        hook_input = _hook_input("ok")
        result = run_pre_compress(hook_input, logs_dir=str(logs_dir))
        assert result is None

    def test_task_prompt_saved_to_log(self, logs_dir):
        prompt = "Implement the authentication module with JWT tokens and refresh logic"
        hook_input = _hook_input(prompt)
        run_pre_compress(hook_input, logs_dir=str(logs_dir))

        today = date.today().isoformat()
        log_file = logs_dir / f"{today}.md"
        assert log_file.exists()
        content = log_file.read_text()
        assert "### [DECISION]" in content
        assert "Implement the authentication" in content

    def test_entry_written_with_arousal(self, logs_dir):
        prompt = "Implement feature X with careful attention to edge cases and error handling"
        hook_input = _hook_input(prompt)
        run_pre_compress(hook_input, logs_dir=str(logs_dir))

        today = date.today().isoformat()
        log_file = logs_dir / f"{today}.md"
        content = log_file.read_text()
        assert "Arousal:" in content

    def test_appends_to_existing_log(self, logs_dir):
        today = date.today().isoformat()
        log_file = logs_dir / f"{today}.md"
        log_file.write_text("# Existing log\n\n### [INSIGHT] Prior entry\n*Arousal: 0.8*\nExisting content.\n")

        prompt = "New task: refactor the database layer to use connection pooling"
        hook_input = _hook_input(prompt)
        run_pre_compress(hook_input, logs_dir=str(logs_dir))

        content = log_file.read_text()
        assert "Prior entry" in content
        assert "connection pooling" in content

    def test_no_logs_dir_does_not_raise(self, tmp_path):
        hook_input = _hook_input("Implement feature Y with full test coverage")
        run_pre_compress(hook_input, logs_dir=str(tmp_path / "nonexistent" / "logs"))

    def test_boundary_prompt_length(self, logs_dir):
        # Exactly 19 chars → ignored
        short_prompt = "A" * 19
        run_pre_compress(_hook_input(short_prompt), logs_dir=str(logs_dir))
        today = date.today().isoformat()
        log_file = logs_dir / f"{today}.md"
        assert not log_file.exists()

        # Exactly 20 chars → saved
        exact_prompt = "A" * 20
        run_pre_compress(_hook_input(exact_prompt), logs_dir=str(logs_dir))
        assert log_file.exists()
