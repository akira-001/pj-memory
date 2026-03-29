"""Global wrap lock to prevent concurrent session wrap operations."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path


_DEFAULT_LOCK_FILE = Path.home() / ".claude" / "wrap.lock"


def _get_lock_file() -> Path:
    env = os.environ.get("COGMEM_WRAP_LOCK_FILE")
    if env:
        return Path(env)
    return _DEFAULT_LOCK_FILE


def _is_alive(pid: int) -> bool:
    """Return True if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it
        return True


class WrapLockError(Exception):
    pass


class WrapLock:
    def __init__(self, lock_file: Path | None = None):
        self._lock_file = lock_file if lock_file is not None else _get_lock_file()

    def acquire(
        self,
        project: str = "",
        timeout: float = 60.0,
        poll_interval: float = 1.0,
    ) -> None:
        """Acquire the wrap lock. Blocks until acquired or timeout."""
        deadline = time.monotonic() + timeout

        while True:
            # Try to clear stale lock first
            self._clear_stale()

            if not self._lock_file.exists():
                self._write_lock(project)
                return

            if time.monotonic() >= deadline:
                holder = self._read_lock()
                holder_info = holder.get("project", "unknown") if holder else "unknown"
                raise WrapLockError(
                    f"already locked by {holder_info} (timed out after {timeout}s)"
                )

            time.sleep(poll_interval)

    def release(self, force: bool = False) -> None:
        """Release the wrap lock."""
        if not self._lock_file.exists():
            return  # No-op if not locked

        data = self._read_lock()
        if data is None:
            return

        if not force and data.get("pid") != os.getpid():
            raise WrapLockError(
                f"not owner: lock held by PID {data.get('pid')} (project: {data.get('project')})"
            )

        self._lock_file.unlink(missing_ok=True)

    def status(self) -> dict | None:
        """Return lock info dict, or None if not locked (also clears stale locks)."""
        self._clear_stale()
        return self._read_lock()

    def _write_lock(self, project: str) -> None:
        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "pid": os.getpid(),
            "project": project,
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._lock_file.write_text(json.dumps(data))

    def _read_lock(self) -> dict | None:
        if not self._lock_file.exists():
            return None
        try:
            return json.loads(self._lock_file.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def _clear_stale(self) -> None:
        data = self._read_lock()
        if data is None:
            return
        pid = data.get("pid")
        if pid is not None and not _is_alive(pid):
            self._lock_file.unlink(missing_ok=True)

    def __str__(self) -> str:
        data = self._read_lock()
        if data is None:
            return "WrapLock(unlocked)"
        return f"WrapLock(pid={data.get('pid')}, project={data.get('project')})"
