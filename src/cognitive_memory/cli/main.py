"""cogmem CLI entrypoint."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="cogmem",
        description="Cognitive Memory — human-like memory for AI agents",
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("--dir", type=str, default=".", help="Target directory")
    init_parser.add_argument("--lang", type=str, choices=["en", "ja"], default=None,
                             help="Language for templates (en/ja). Prompts interactively if omitted.")

    # index
    index_parser = subparsers.add_parser("index", help="Build/update the memory index")
    index_parser.add_argument("--all", action="store_true", help="Force re-index all files")
    index_parser.add_argument("--file", type=str, help="Index a specific file")

    # search
    search_parser = subparsers.add_parser("search", help="Search memories")
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    search_parser.add_argument("--json", action="store_true", help="JSON output")

    # status
    subparsers.add_parser("status", help="Show index statistics")

    # signals
    subparsers.add_parser("signals", help="Check crystallization signals")

    # migrate
    migrate_parser = subparsers.add_parser("migrate", help="Upgrade project files from older versions")
    migrate_parser.add_argument("--dir", type=str, default=".", help="Target directory")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        from .init_cmd import run_init
        run_init(args.dir, lang=args.lang)
    elif args.command == "index":
        from .index_cmd import run_index
        run_index(all_files=args.all, single_file=args.file)
    elif args.command == "search":
        from .search_cmd import run_search
        run_search(query=args.query, top_k=args.top_k, json_output=args.json)
    elif args.command == "status":
        from .index_cmd import run_status
        run_status()
    elif args.command == "signals":
        from .signals_cmd import run_signals
        run_signals()
    elif args.command == "migrate":
        from .migrate_cmd import run_migrate
        run_migrate(args.dir)
