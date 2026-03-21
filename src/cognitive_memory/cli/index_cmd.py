"""cogmem index / cogmem status — index management commands."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from ..config import CogMemConfig
from ..store import MemoryStore


def run_index(all_files: bool = False, single_file: str | None = None):
    config = CogMemConfig.find_and_load()

    with MemoryStore(config) as store:
        t0 = time.time()

        if single_file:
            fp = config.logs_path / Path(single_file).name
            if not fp.exists():
                print(f"File not found: {fp}", file=sys.stderr)
                sys.exit(1)
            n = store.index_file(fp, force=True)
            print(f"Indexed {n} entries from {fp.name}")
        else:
            n = store.index_dir(force=all_files)
            elapsed = time.time() - t0
            print(f"Done: {n} entries indexed in {elapsed:.1f}s")


def run_status():
    config = CogMemConfig.find_and_load()

    with MemoryStore(config) as store:
        stats = store.status()

    print(f"Indexed files: {stats['indexed_files']}")
    print(f"Total entries: {stats['total_entries']}")
    size_kb = stats["db_size_bytes"] / 1024
    print(f"Database size: {size_kb:.1f} KB")
