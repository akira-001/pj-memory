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
    init_parser.add_argument("--user-id", type=str, default=None,
                             help="User ID for log isolation (prompts interactively if omitted)")

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
    migrate_parser.add_argument("--user-id", type=str, default=None,
                                help="User ID for log isolation (prompts interactively if omitted)")

    # dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Start the web dashboard")
    dash_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    dash_parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    dash_parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")

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

    # skills resolve
    skills_resolve_parser = skills_subparsers.add_parser("resolve", help="Mark skill events as resolved after SKILL.md edit")
    skills_resolve_parser.add_argument("skill_name", type=str, help="Skill name to resolve")
    skills_resolve_parser.add_argument("--no-version", action="store_true", help="Resolve without incrementing version (for user-directed fixes)")

    # skills suggest
    skills_suggest_parser = skills_subparsers.add_parser("suggest", help="Record a skill creation suggestion")
    skills_suggest_parser.add_argument("context", type=str, help="Short label for the pattern (e.g. 'PM2デバッグ')")
    skills_suggest_parser.add_argument("--description", type=str, default="", help="What the pattern involves")

    # skills suggest-summary
    skills_ss_parser = skills_subparsers.add_parser("suggest-summary", help="Show recurring suggestions ready for promotion")
    skills_ss_parser.add_argument("--min-count", type=int, default=2, dest="min_count", help="Minimum occurrences (default: 2)")
    skills_ss_parser.add_argument("--json", action="store_true", help="JSON output")

    # skills promote
    skills_promote_parser = skills_subparsers.add_parser("promote", help="Mark a suggestion as promoted (skill was created)")
    skills_promote_parser.add_argument("context", type=str, help="The suggestion context label to promote")

    # readme
    readme_parser = subparsers.add_parser("readme", help="Display the package README")
    readme_parser.add_argument("--lang", type=str, choices=["en", "ja"], default="en",
                               help="Language (default: en)")

    # decay
    decay_parser = subparsers.add_parser("decay", help="Apply memory decay to consolidated logs")
    decay_parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    decay_parser.add_argument("--json", action="store_true", help="JSON output")

    # recall-stats
    recall_parser = subparsers.add_parser("recall-stats", help="Show recall statistics")
    recall_parser.add_argument("--json", action="store_true", dest="json_output", help="JSON output")

    # watch
    watch_parser = subparsers.add_parser("watch", help="Detect patterns from git history")
    watch_parser.add_argument("--since", type=str, default="today", help="Git log --since value")
    watch_parser.add_argument("--json", action="store_true", help="JSON output")
    watch_parser.add_argument("--auto-log", action="store_true", help="Auto-append detected patterns to session log")

    # hook subcommand group
    hook_parser = subparsers.add_parser("hook", help="Claude Code hook handlers")
    hook_subparsers = hook_parser.add_subparsers(dest="hook_command")
    hook_subparsers.add_parser("failure-breaker", help="Detect consecutive command failures")
    hook_subparsers.add_parser("skill-gate", help="Check skill usage for edited files")

    # wrap subcommand group
    wrap_parser = subparsers.add_parser("wrap", help="Manage wrap lock for concurrent session safety")
    wrap_subparsers = wrap_parser.add_subparsers(dest="wrap_command")

    # wrap lock
    wrap_lock_parser = wrap_subparsers.add_parser("lock", help="Acquire the wrap lock")
    wrap_lock_parser.add_argument("--project", type=str, default="", help="Project path (for identification)")
    wrap_lock_parser.add_argument("--timeout", type=float, default=60.0, help="Max wait seconds (default: 60)")

    # wrap unlock
    wrap_subparsers.add_parser("unlock", help="Release the wrap lock")

    # wrap status
    wrap_status_parser = wrap_subparsers.add_parser("status", help="Show current lock status")
    wrap_status_parser.add_argument("--json", action="store_true", help="JSON output")

    # identity subcommand group
    identity_parser = subparsers.add_parser("identity", help="View and update identity files")
    identity_subparsers = identity_parser.add_subparsers(dest="identity_command")

    # identity update
    id_update_parser = identity_subparsers.add_parser("update", help="Update identity file sections")
    id_update_parser.add_argument("--target", type=str, required=True, choices=["user", "soul"],
                                  help="Target identity file")
    id_update_parser.add_argument("--section", type=str, default=None, help="Section heading to update")
    id_update_parser.add_argument("--content", type=str, default=None, help="New content for section")
    id_update_parser.add_argument("--json", type=str, default=None, dest="json_input",
                                  help='JSON object of {section: content} pairs')

    # identity show
    id_show_parser = identity_subparsers.add_parser("show", help="Show identity file contents")
    id_show_parser.add_argument("--target", type=str, default=None, choices=["user", "soul"],
                                help="Target identity file (omit for both)")

    # identity detect
    id_detect_parser = identity_subparsers.add_parser("detect", help="Detect placeholder sections")
    id_detect_parser.add_argument("--target", type=str, default=None, choices=["user", "soul"],
                                  help="Target identity file (omit for both)")
    id_detect_parser.add_argument("--json", action="store_true", dest="json_output",
                                  help="JSON output")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        from .init_cmd import run_init
        run_init(args.dir, lang=args.lang, user_id=args.user_id)
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
        run_migrate(args.dir, user_id=args.user_id)
    elif args.command == "dashboard":
        from .dashboard_cmd import run_dashboard
        run_dashboard(host=args.host, port=args.port, no_browser=args.no_browser)
    elif args.command == "skills":
        from .skills_cmd import run_skills
        run_skills(args)
    elif args.command == "readme":
        from .readme_cmd import run_readme
        run_readme(lang=args.lang)
    elif args.command == "decay":
        from .decay_cmd import run_decay
        run_decay(dry_run=args.dry_run, json_output=args.json)
    elif args.command == "recall-stats":
        from .recall_cmd import run_recall_stats
        run_recall_stats(json_output=args.json_output)
    elif args.command == "watch":
        from .watch_cmd import run_watch
        run_watch(since=args.since, json_output=args.json, auto_log=args.auto_log)
    elif args.command == "hook":
        from .hook_cmd import run_hook
        run_hook(args)
    elif args.command == "wrap":
        from .wrap_cmd import run_wrap
        run_wrap(args)
    elif args.command == "identity":
        from .identity_cmd import run_identity_update, run_identity_show, run_identity_detect
        if args.identity_command == "update":
            run_identity_update(
                target=args.target, section=args.section,
                content=args.content, json_input=args.json_input,
            )
        elif args.identity_command == "show":
            run_identity_show(target=args.target)
        elif args.identity_command == "detect":
            run_identity_detect(target=args.target, json_output=args.json_output)
        else:
            identity_parser.print_help()
            sys.exit(1)
