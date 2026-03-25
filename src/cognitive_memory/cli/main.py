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

    # context-search
    ctx_parser = subparsers.add_parser("context-search", help="Context-aware memory search")
    ctx_parser.add_argument("query", type=str, help="Search query")
    ctx_parser.add_argument("--top-k", type=int, default=3, help="Number of results")
    ctx_parser.add_argument("--json", action="store_true", help="JSON output")
    ctx_parser.add_argument("--keywords", nargs="*", type=str, help="Session keywords for gate")

    # status
    subparsers.add_parser("status", help="Show index statistics")

    # signals
    subparsers.add_parser("signals", help="Check crystallization signals")

    # migrate
    migrate_parser = subparsers.add_parser("migrate", help="Upgrade project files from older versions")
    migrate_parser.add_argument("--dir", type=str, default=".", help="Target directory")

    # skills subcommand group
    skills_parser = subparsers.add_parser("skills", help="Manage skills (Memento-Skills)")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command")

    # skills list
    skills_list_parser = skills_subparsers.add_parser("list", help="List all skills")
    skills_list_parser.add_argument("--category", type=str, help="Filter by category")
    skills_list_parser.add_argument("--top", type=int, default=10, help="Show top N skills")
    skills_list_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills search
    skills_search_parser = skills_subparsers.add_parser("search", help="Search skills")
    skills_search_parser.add_argument("query", type=str, help="Search query")
    skills_search_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    skills_search_parser.add_argument("--category", type=str, help="Filter by category")
    skills_search_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills show
    skills_show_parser = skills_subparsers.add_parser("show", help="Show skill details")
    skills_show_parser.add_argument("skill_id", type=str, help="Skill ID")
    skills_show_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills stats
    skills_stats_parser = skills_subparsers.add_parser("stats", help="Show skills statistics")
    skills_stats_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills create
    skills_create_parser = skills_subparsers.add_parser("create", help="Create new skill")
    skills_create_parser.add_argument("context", type=str, help="Context for skill creation")
    skills_create_parser.add_argument("--effectiveness", type=float, default=0.5, help="Initial effectiveness (0-1)")
    skills_create_parser.add_argument("--user-satisfaction", type=float, default=0.5, help="Initial user satisfaction (0-1)")
    skills_create_parser.add_argument("--feedback", type=str, default="", help="User feedback")

    # skills delete
    skills_delete_parser = skills_subparsers.add_parser("delete", help="Delete a skill")
    skills_delete_parser.add_argument("skill_id", type=str, help="Skill ID to delete")

    # skills learn
    skills_learn_parser = skills_subparsers.add_parser("learn", help="Execute learning loop")
    skills_learn_parser.add_argument("context", type=str, help="Context for learning")
    skills_learn_parser.add_argument("--effectiveness", type=float, required=True, help="Effectiveness score (0-1)")
    skills_learn_parser.add_argument("--user-satisfaction", type=float, required=True, help="User satisfaction (0-1)")
    skills_learn_parser.add_argument("--execution-time", type=float, default=1000, help="Execution time in ms")
    skills_learn_parser.add_argument("--error-rate", type=float, default=0.0, help="Error rate (0-1)")
    skills_learn_parser.add_argument("--feedback", type=str, default="", help="User feedback")
    skills_learn_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills export
    skills_export_parser = skills_subparsers.add_parser("export", help="Export skills to .claude/skills/ markdown files")
    skills_export_parser.add_argument("--output-dir", type=str, default=None, help="Output directory (default: .claude/skills/)")
    skills_export_parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    skills_export_parser.add_argument("--quiet", action="store_true", help="Suppress per-file output")

    # skills import
    skills_import_parser = skills_subparsers.add_parser("import", help="Import skills from .claude/skills/ markdown files")
    skills_import_parser.add_argument("source_dir", type=str, help="Directory containing skill markdown files")
    skills_import_parser.add_argument("--force", action="store_true", help="Overwrite existing skills in DB")
    skills_import_parser.add_argument("--quiet", action="store_true", help="Suppress per-file output")

    # skills audit
    skills_audit_parser = skills_subparsers.add_parser("audit", help="Audit skills and recommend improvements")
    skills_audit_parser.add_argument("--brief", action="store_true", help="Quick check (skip slow scans)")
    skills_audit_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills review
    skills_review_parser = skills_subparsers.add_parser("review", help="Full skill health review with recommendations")
    skills_review_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills ingest
    skills_ingest_parser = skills_subparsers.add_parser("ingest", help="Ingest skill-creator benchmark results")
    skills_ingest_parser.add_argument("--benchmark", type=str, required=True, help="Path to benchmark workspace directory")
    skills_ingest_parser.add_argument("--skill-name", type=str, required=True, help="Skill name to update")
    skills_ingest_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills track
    skills_track_parser = skills_subparsers.add_parser("track", help="Track a skill usage event during a session")
    skills_track_parser.add_argument("skill_name", type=str, help="Skill name (directory name)")
    skills_track_parser.add_argument("--event", type=str, required=True,
                                     choices=["extra_step", "skipped_step", "error_recovery", "user_correction"],
                                     help="Event type")
    skills_track_parser.add_argument("--description", type=str, required=True, help="What happened")
    skills_track_parser.add_argument("--step", type=str, default=None, help="Step reference (e.g. 'Step 3')")
    skills_track_parser.add_argument("--date", type=str, default=None, help="Session date (default: today)")

    # skills track-summary
    skills_ts_parser = skills_subparsers.add_parser("track-summary", help="Summarize tracked events for a session")
    skills_ts_parser.add_argument("--date", type=str, default=None, help="Session date (default: today)")
    skills_ts_parser.add_argument("--json", action="store_true", help="JSON output")

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
    elif args.command == "context-search":
        from .context_search_cmd import run_context_search
        run_context_search(query=args.query, top_k=args.top_k, json_output=args.json, keywords=args.keywords)
    elif args.command == "status":
        from .index_cmd import run_status
        run_status()
    elif args.command == "signals":
        from .signals_cmd import run_signals
        run_signals()
    elif args.command == "migrate":
        from .migrate_cmd import run_migrate
        run_migrate(args.dir)
    elif args.command == "skills":
        from .skills_cmd import run_skills
        run_skills(args)
