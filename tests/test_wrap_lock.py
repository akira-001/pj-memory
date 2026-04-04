"""Tests for cogmem wrap lock/unlock/status commands."""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from cognitive_memory.wrap_lock import WrapLock, WrapLockError


class TestWrapLockAcquire:
    def test_acquire_creates_lock_file(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock = WrapLock(lock_file)

        lock.acquire(project="/test/project")

        assert lock_file.exists()

    def test_lock_file_contains_pid_and_project(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock = WrapLock(lock_file)

        lock.acquire(project="/test/project")

        data = json.loads(lock_file.read_text())
        assert data["pid"] == os.getpid()
        assert data["project"] == "/test/project"
        assert "started_at" in data

    def test_acquire_raises_if_lock_held_by_live_process(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        # Write lock held by current process (always alive)
        lock_data = {"pid": os.getpid(), "project": "/other/project", "started_at": "2026-01-01T00:00:00"}
        lock_file.write_text(json.dumps(lock_data))

        lock = WrapLock(lock_file)
        with pytest.raises(WrapLockError, match="already locked"):
            lock.acquire(project="/test/project", timeout=0)

    def test_acquire_clears_stale_lock_from_dead_process(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        # PID 99999 almost certainly doesn't exist
        lock_data = {"pid": 99999, "project": "/dead/project", "started_at": "2026-01-01T00:00:00"}
        lock_file.write_text(json.dumps(lock_data))

        lock = WrapLock(lock_file)
        lock.acquire(project="/test/project", timeout=0)

        data = json.loads(lock_file.read_text())
        assert data["project"] == "/test/project"
        assert data["pid"] == os.getpid()

    def test_acquire_waits_and_succeeds_when_lock_released(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock = WrapLock(lock_file)
        lock.acquire(project="/first/project")

        # Release after short delay in background
        import threading
        def release_soon():
            time.sleep(0.2)
            lock_file.unlink()

        t = threading.Thread(target=release_soon)
        t.start()

        lock2 = WrapLock(lock_file)
        lock2.acquire(project="/second/project", timeout=2, poll_interval=0.05)
        t.join()

        data = json.loads(lock_file.read_text())
        assert data["project"] == "/second/project"

    def test_acquire_times_out_if_lock_never_released(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock_data = {"pid": os.getpid(), "project": "/blocking/project", "started_at": "2026-01-01T00:00:00"}
        lock_file.write_text(json.dumps(lock_data))

        lock = WrapLock(lock_file)
        with pytest.raises(WrapLockError, match="timed out"):
            lock.acquire(project="/test/project", timeout=0.1, poll_interval=0.05)


class TestWrapLockRelease:
    def test_unlock_removes_lock_file(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock = WrapLock(lock_file)
        lock.acquire(project="/test/project")

        lock.release()

        assert not lock_file.exists()

    def test_unlock_only_removes_own_project_lock(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock_data = {"pid": 99999, "project": "/other/project", "started_at": "2026-01-01T00:00:00"}
        lock_file.write_text(json.dumps(lock_data))

        lock = WrapLock(lock_file)
        with pytest.raises(WrapLockError, match="not owner"):
            lock.release(project="/different/project")

    def test_unlock_succeeds_for_same_project_different_pid(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock_data = {"pid": 99999, "project": "/test/project", "started_at": "2026-01-01T00:00:00"}
        lock_file.write_text(json.dumps(lock_data))

        lock = WrapLock(lock_file)
        lock.release(project="/test/project")

        assert not lock_file.exists()

    def test_unlock_without_project_always_succeeds(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock_data = {"pid": 99999, "project": "/other/project", "started_at": "2026-01-01T00:00:00"}
        lock_file.write_text(json.dumps(lock_data))

        lock = WrapLock(lock_file)
        lock.release()  # no project specified = no ownership check

        assert not lock_file.exists()

    def test_unlock_when_no_lock_is_noop(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock = WrapLock(lock_file)

        # Should not raise
        lock.release(force=True)


class TestWrapLockStatus:
    def test_status_returns_none_when_no_lock(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock = WrapLock(lock_file)

        assert lock.status() is None

    def test_status_returns_lock_info_when_locked(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock = WrapLock(lock_file)
        lock.acquire(project="/test/project")

        status = lock.status()

        assert status["pid"] == os.getpid()
        assert status["project"] == "/test/project"

    def test_status_clears_stale_lock_and_returns_none(self, tmp_path):
        lock_file = tmp_path / "wrap.lock"
        lock_data = {"pid": 99999, "project": "/dead/project", "started_at": "2026-01-01T00:00:00"}
        lock_file.write_text(json.dumps(lock_data))

        lock = WrapLock(lock_file)
        status = lock.status()

        assert status is None
        assert not lock_file.exists()


class TestWrapLockCLI:
    def test_cli_lock_command(self, tmp_path, monkeypatch):
        from cognitive_memory.cli.main import main as cli_main
        lock_file = tmp_path / "wrap.lock"
        monkeypatch.setenv("COGMEM_WRAP_LOCK_FILE", str(lock_file))

        cli_main(["wrap", "lock", "--project", "/test/project"])

        assert lock_file.exists()

    def test_cli_unlock_command(self, tmp_path, monkeypatch):
        from cognitive_memory.cli.main import main as cli_main
        lock_file = tmp_path / "wrap.lock"
        monkeypatch.setenv("COGMEM_WRAP_LOCK_FILE", str(lock_file))

        cli_main(["wrap", "lock", "--project", "/test/project"])
        cli_main(["wrap", "unlock", "--project", "/test/project"])

        assert not lock_file.exists()

    def test_cli_status_outputs_json_when_locked(self, tmp_path, monkeypatch, capsys):
        from cognitive_memory.cli.main import main as cli_main
        lock_file = tmp_path / "wrap.lock"
        monkeypatch.setenv("COGMEM_WRAP_LOCK_FILE", str(lock_file))

        cli_main(["wrap", "lock", "--project", "/test/project"])
        capsys.readouterr()  # clear lock output
        cli_main(["wrap", "status", "--json"])

        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["locked"] is True
        assert data["project"] == "/test/project"

    def test_cli_status_outputs_json_when_unlocked(self, tmp_path, monkeypatch, capsys):
        from cognitive_memory.cli.main import main as cli_main
        lock_file = tmp_path / "wrap.lock"
        monkeypatch.setenv("COGMEM_WRAP_LOCK_FILE", str(lock_file))

        cli_main(["wrap", "status", "--json"])

        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["locked"] is False
