"""CLI commands for wrap lock management."""

from __future__ import annotations

import json
import sys

from cognitive_memory.wrap_lock import WrapLock, WrapLockError


def run_wrap(args) -> None:
    lock = WrapLock()

    if args.wrap_command == "lock":
        try:
            lock.acquire(
                project=args.project or "",
                timeout=args.timeout,
            )
            print(f"Lock acquired (project: {args.project})")
        except WrapLockError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.wrap_command == "unlock":
        try:
            lock.release()
            print("Lock released")
        except WrapLockError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.wrap_command == "status":
        status = lock.status()
        if args.json:
            if status is None:
                print(json.dumps({"locked": False}))
            else:
                print(json.dumps({"locked": True, **status}))
        else:
            if status is None:
                print("Not locked")
            else:
                print(
                    f"Locked by PID {status['pid']} "
                    f"(project: {status.get('project', 'unknown')}, "
                    f"since: {status.get('started_at', 'unknown')})"
                )
    else:
        print("Usage: cogmem wrap <lock|unlock|status>", file=sys.stderr)
        sys.exit(1)
