"""Skills management CLI commands."""

from __future__ import annotations

import json
import re
import sys
import asyncio
from pathlib import Path
from typing import Any

from ..config import CogMemConfig
from ..skills import SkillsManager, PerformanceMetric, SKILL_CATEGORIES


def run_skills(args):
    """Run skills management commands."""
    if not args.skills_command:
        print("No skills subcommand specified. Use 'cogmem skills --help' for usage.")
        sys.exit(1)

    try:
        config = CogMemConfig.find_and_load()
    except FileNotFoundError:
        print("Error: No cogmem.toml found. Initialize a project first with 'cogmem init'.")
        sys.exit(1)

    skills_manager = SkillsManager(config)

    if args.skills_command == "list":
        run_skills_list(skills_manager, args)
    elif args.skills_command == "search":
        run_skills_search(skills_manager, args)
    elif args.skills_command == "show":
        run_skills_show(skills_manager, args)
    elif args.skills_command == "stats":
        run_skills_stats(skills_manager, args)
    elif args.skills_command == "create":
        asyncio.run(run_skills_create(skills_manager, args))
    elif args.skills_command == "delete":
        run_skills_delete(skills_manager, args)
    elif args.skills_command == "learn":
        asyncio.run(run_skills_learn(skills_manager, args))
    elif args.skills_command == "export":
        run_skills_export(skills_manager, args, config)
    elif args.skills_command == "import":
        run_skills_import(skills_manager, args)
    elif args.skills_command == "audit":
        run_skills_audit(skills_manager, args)
    elif args.skills_command == "review":
        run_skills_review(skills_manager, args)
    elif args.skills_command == "ingest":
        run_skills_ingest(skills_manager, args)
    elif args.skills_command == "track":
        run_skills_track(skills_manager, args)
    elif args.skills_command == "track-summary":
        run_skills_track_summary(skills_manager, args)
    elif args.skills_command == "resolve":
        increment = not getattr(args, 'no_version', False)
        count = skills_manager.store.resolve_events(args.skill_name, increment_version=increment)
        version_note = " (version incremented)" if increment and count > 0 else " (version unchanged)"
        print(f"Resolved {count} events for {args.skill_name}{version_note}")
    elif args.skills_command == "suggest":
        run_skills_suggest(skills_manager, args)
    elif args.skills_command == "suggest-summary":
        run_skills_suggest_summary(skills_manager, args)
    elif args.skills_command == "promote":
        count = skills_manager.store.promote_suggestion(args.context)
        if count > 0:
            print(f"Promoted {count} suggestion(s) for '{args.context}'")
        else:
            print(f"No unpromoted suggestions found for '{args.context}'")
    elif args.skills_command == "dismiss":
        count = skills_manager.store.dismiss_suggestion(args.context)
        if count > 0:
            print(f"Dismissed {count} suggestion(s) for '{args.context}'")
        else:
            print(f"No pending suggestions found for '{args.context}'")
    elif args.skills_command == "check-updates":
        run_skills_check_updates(config, args)
    else:
        print(f"Unknown skills command: {args.skills_command}")
        sys.exit(1)


def run_skills_list(skills_manager: SkillsManager, args):
    """List skills."""
    if args.category:
        if args.category not in SKILL_CATEGORIES:
            print(f"Error: Invalid category '{args.category}'. Valid categories: {', '.join(SKILL_CATEGORIES)}")
            sys.exit(1)
        skills = skills_manager.get_skills_by_category(args.category)
    else:
        skills = skills_manager.get_top_skills(limit=args.top)

    if args.json:
        skills_data = []
        for skill in skills:
            skills_data.append({
                "id": skill.id,
                "name": skill.name,
                "category": skill.category,
                "description": skill.description,
                "average_effectiveness": skill.usage_stats.average_effectiveness,
                "total_executions": skill.usage_stats.total_executions,
                "created_at": skill.created_at,
                "updated_at": skill.updated_at,
                "version": skill.version
            })
        print(json.dumps(skills_data, indent=2))
    else:
        if not skills:
            print("No skills found.")
            return

        print(f"\n{'ID':<20} {'Name':<25} {'Category':<18} {'Effectiveness':<12} {'Executions':<10}")
        print("-" * 90)

        for skill in skills:
            print(f"{skill.id[:18]:<20} {skill.name[:23]:<25} {skill.category:<18} "
                  f"{skill.usage_stats.average_effectiveness:.3f}        {skill.usage_stats.total_executions:<10}")

        print(f"\nTotal: {len(skills)} skills")


def run_skills_search(skills_manager: SkillsManager, args):
    """Search skills."""
    skills = skills_manager.search_skills(
        query=args.query,
        category=args.category,
        top_k=args.top_k
    )

    if args.json:
        skills_data = []
        for skill in skills:
            skills_data.append({
                "id": skill.id,
                "name": skill.name,
                "category": skill.category,
                "description": skill.description,
                "average_effectiveness": skill.usage_stats.average_effectiveness,
                "total_executions": skill.usage_stats.total_executions
            })
        print(json.dumps(skills_data, indent=2))
    else:
        if not skills:
            print(f"No skills found for query: '{args.query}'")
            return

        print(f"\nFound {len(skills)} skills for query: '{args.query}'")
        print(f"\n{'ID':<20} {'Name':<25} {'Category':<18} {'Effectiveness':<12}")
        print("-" * 80)

        for skill in skills:
            print(f"{skill.id[:18]:<20} {skill.name[:23]:<25} {skill.category:<18} {skill.usage_stats.average_effectiveness:.3f}")


def run_skills_show(skills_manager: SkillsManager, args):
    """Show skill details."""
    # Find skill by ID across all categories
    all_skills = skills_manager.load_all_skills()
    target_skill = None

    for category_skills in all_skills.values():
        for skill in category_skills:
            if skill.id == args.skill_id:
                target_skill = skill
                break
        if target_skill:
            break

    if not target_skill:
        print(f"Skill not found: {args.skill_id}")
        sys.exit(1)

    if args.json:
        skill_data = {
            "id": target_skill.id,
            "name": target_skill.name,
            "category": target_skill.category,
            "description": target_skill.description,
            "execution_pattern": target_skill.execution_pattern,
            "success_metrics": [
                {
                    "name": m.name,
                    "description": m.description,
                    "measurement_method": m.measurement_method,
                    "target_value": m.target_value,
                    "current_value": m.current_value
                }
                for m in target_skill.success_metrics
            ],
            "usage_stats": {
                "total_executions": target_skill.usage_stats.total_executions,
                "successful_executions": target_skill.usage_stats.successful_executions,
                "average_effectiveness": target_skill.usage_stats.average_effectiveness,
                "last_used_at": target_skill.usage_stats.last_used_at,
                "frequency": target_skill.usage_stats.frequency
            },
            "improvement_history": [
                {
                    "timestamp": r.timestamp,
                    "description": r.description,
                    "effectiveness_gain": r.effectiveness_gain
                }
                for r in target_skill.improvement_history
            ],
            "created_at": target_skill.created_at,
            "updated_at": target_skill.updated_at,
            "version": target_skill.version
        }
        print(json.dumps(skill_data, indent=2))
    else:
        print(f"\nSkill Details: {target_skill.name}")
        print("=" * 50)
        print(f"ID: {target_skill.id}")
        print(f"Category: {target_skill.category}")
        print(f"Description: {target_skill.description}")
        print(f"\nPerformance:")
        print(f"  Average Effectiveness: {target_skill.usage_stats.average_effectiveness:.3f}")
        print(f"  Total Executions: {target_skill.usage_stats.total_executions}")
        print(f"  Successful Executions: {target_skill.usage_stats.successful_executions}")
        print(f"  Success Rate: {target_skill.usage_stats.successful_executions / target_skill.usage_stats.total_executions * 100:.1f}%"
              if target_skill.usage_stats.total_executions > 0 else "  Success Rate: N/A")
        print(f"  Last Used: {target_skill.usage_stats.last_used_at or 'Never'}")

        if target_skill.improvement_history:
            print(f"\nImprovement History ({len(target_skill.improvement_history)} records):")
            for i, record in enumerate(target_skill.improvement_history[-3:], 1):  # Show last 3
                print(f"  {i}. {record.timestamp}: +{record.effectiveness_gain:.3f} - {record.description}")

        print(f"\nCreated: {target_skill.created_at}")
        print(f"Updated: {target_skill.updated_at}")
        print(f"Version: {target_skill.version}")


def run_skills_stats(skills_manager: SkillsManager, args):
    """Show skills statistics."""
    stats = skills_manager.get_skill_stats()

    if args.json:
        print(json.dumps(stats, indent=2, default=str))
    else:
        print("\nSkills Statistics")
        print("=" * 30)
        print(f"Total Skills: {stats['total_skills']}")
        print(f"Average Effectiveness: {stats['average_effectiveness']:.3f}")
        print(f"Total Executions: {stats['total_executions']}")
        print(f"Overall Success Rate: {stats['overall_success_rate']:.3f}")

        print(f"\nSkills by Category:")
        for category, count in stats['category_counts'].items():
            print(f"  {category}: {count}")

        if stats['most_effective_skills']:
            print(f"\nTop Performing Skills:")
            for i, skill in enumerate(stats['most_effective_skills'][:5], 1):
                print(f"  {i}. {skill.name} ({skill.usage_stats.average_effectiveness:.3f})")


async def run_skills_create(skills_manager: SkillsManager, args):
    """Create a new skill."""
    performance = PerformanceMetric(
        effectiveness=args.effectiveness,
        user_satisfaction=args.user_satisfaction,
        execution_time=1000.0,  # Default
        error_rate=0.0          # Default
    )

    try:
        new_skill = skills_manager.create_skill_from_context(
            context=args.context,
            performance=performance,
            user_feedback=args.feedback
        )

        print(f"Created new skill: {new_skill.name}")
        print(f"ID: {new_skill.id}")
        print(f"Category: {new_skill.category}")

    except Exception as e:
        print(f"Error creating skill: {e}")
        sys.exit(1)


def run_skills_delete(skills_manager: SkillsManager, args):
    """Delete a skill."""
    if skills_manager.delete_skill(args.skill_id):
        print(f"Deleted skill: {args.skill_id}")
    else:
        print(f"Skill not found: {args.skill_id}")
        sys.exit(1)


async def run_skills_learn(skills_manager: SkillsManager, args):
    """Execute learning loop."""
    performance = PerformanceMetric(
        effectiveness=args.effectiveness,
        user_satisfaction=args.user_satisfaction,
        execution_time=args.execution_time,
        error_rate=args.error_rate
    )

    try:
        result = await skills_manager.execute_learning_loop(
            context=args.context,
            performance=performance,
            user_feedback=args.feedback
        )

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"\nLearning Loop Results")
            print("=" * 30)
            print(f"Skills Analyzed: {result['learning_summary']['skills_analyzed']}")
            print(f"Selected Skill: {result['learning_summary']['skill_selected']}")
            print(f"Learning Action: {result['learning_summary']['learning_action']}")
            print(f"Performance Level: {result['learning_summary']['performance_level']}")

            if result['write_phase']['action'] == 'create':
                skill = result['write_phase']['skill']
                print(f"\nNew Skill Created:")
                print(f"  Name: {skill['name']}")
                print(f"  ID: {skill['id']}")
                print(f"  Category: {skill['category']}")

            if result['learning_summary']['key_insights']:
                print(f"\nKey Insights:")
                for insight in result['learning_summary']['key_insights']:
                    print(f"  • {insight}")

    except Exception as e:
        print(f"Error executing learning loop: {e}")
        sys.exit(1)


def _skill_to_markdown(skill) -> str:
    """Convert a Skill object to markdown format for .claude/skills/."""
    lines = []
    # YAML frontmatter for Claude Code native skill matching
    lines.append("---")
    lines.append(f"description: {skill.description}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {skill.name}")
    lines.append("")
    lines.append(f"*Category: {skill.category} | Effectiveness: {skill.usage_stats.average_effectiveness:.2f} | Version: {skill.version}*")
    lines.append(f"*Skill ID: {skill.id}*")
    lines.append("")
    lines.append("## 手順")
    for i, step in enumerate(skill.execution_pattern.split("\n"), 1):
        step = step.strip()
        if step:
            if step[0].isdigit():
                lines.append(step)
            else:
                lines.append(f"{i}. {step}")
    lines.append("")
    if skill.success_metrics:
        lines.append("## 成功指標")
        for metric in skill.success_metrics:
            target = f" (target: {metric.target_value})" if metric.target_value else ""
            lines.append(f"- {metric.name}: {metric.description}{target}")
        lines.append("")
    return "\n".join(lines)


def _slugify(name: str) -> str:
    """Convert skill name to filename-safe slug (max 50 chars)."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\u3040-\u9fff\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    if len(slug) > 50:
        slug = slug[:50].rsplit('-', 1)[0]
    return slug or "skill"


def run_skills_export(skills_manager: SkillsManager, args, config: CogMemConfig):
    """Export skills from DB to .claude/skills/ markdown files."""
    target_dir = Path(args.output_dir) if args.output_dir else Path(config.project_root) / ".claude" / "skills"
    target_dir.mkdir(parents=True, exist_ok=True)

    all_skills = skills_manager.load_all_skills()
    all_skills_flat = [skill for skills in all_skills.values() for skill in skills]

    if not all_skills_flat:
        print("No skills found in database.")
        return

    exported = 0
    skipped = 0
    for skill in all_skills_flat:
        filename = _slugify(skill.name) + ".md"
        filepath = target_dir / filename

        if filepath.exists() and not args.force:
            skipped += 1
            continue

        content = _skill_to_markdown(skill)
        filepath.write_text(content, encoding="utf-8")
        exported += 1
        if not args.quiet:
            print(f"Exported: {filepath}")

    print(f"\nExported {exported} skills to {target_dir}")
    if skipped:
        print(f"Skipped {skipped} existing files (use --force to overwrite)")


def _parse_skill_markdown(filepath: Path) -> dict:
    """Parse a .claude/skills/ markdown file into skill attributes."""
    content = filepath.read_text(encoding="utf-8")
    result = {
        "name": filepath.stem.replace("-", " ").title(),
        "description": "",
        "execution_pattern": "",
        "skill_id": None,
    }

    lines = content.split("\n")
    current_section = None
    section_lines = {"triggers": [], "steps": []}

    # Parse YAML frontmatter if present
    frontmatter_description = ""
    body_start = 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                body_start = i + 1
                break
            match = re.match(r'^description:\s*(.+)', line)
            if match:
                frontmatter_description = match.group(1).strip()

    for line in lines[body_start:]:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            result["name"] = stripped[2:].strip()
        elif "Skill ID:" in stripped:
            match = re.search(r'Skill ID:\s*(\S+)', stripped)
            if match:
                result["skill_id"] = match.group(1).rstrip("*")
        elif stripped.startswith("## "):
            section_name = stripped[3:].strip().lower()
            if "トリガー" in section_name or "trigger" in section_name:
                current_section = "triggers"
            elif "手順" in section_name or "step" in section_name:
                current_section = "steps"
            else:
                current_section = "other"
        elif current_section == "triggers" and stripped.startswith("- "):
            section_lines["triggers"].append(stripped[2:])
        elif current_section == "steps" and stripped:
            section_lines["steps"].append(stripped)

    # Prefer frontmatter description, fall back to triggers section
    if frontmatter_description:
        result["description"] = frontmatter_description
    elif section_lines["triggers"]:
        result["description"] = ". ".join(section_lines["triggers"])

    result["execution_pattern"] = "\n".join(section_lines["steps"])
    return result


def run_skills_import(skills_manager: SkillsManager, args):
    """Import skills from .claude/skills/ markdown files into DB."""
    source_dir = Path(args.source_dir)
    if not source_dir.is_dir():
        print(f"Error: Directory not found: {source_dir}")
        sys.exit(1)

    md_files = sorted(source_dir.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {source_dir}")
        return

    imported = 0
    skipped = 0
    for filepath in md_files:
        parsed = _parse_skill_markdown(filepath)

        if parsed["skill_id"]:
            existing = None
            for cat_skills in skills_manager.load_all_skills().values():
                for s in cat_skills:
                    if s.id == parsed["skill_id"]:
                        existing = s
                        break
            if existing and not args.force:
                skipped += 1
                continue

        performance = PerformanceMetric(
            effectiveness=0.5,
            user_satisfaction=0.5,
            execution_time=1000.0,
            error_rate=0.0
        )
        try:
            new_skill = skills_manager.create_skill_from_context(
                context=f"{parsed['name']}: {parsed['description']}",
                performance=performance,
                user_feedback=parsed["execution_pattern"][:200]
            )
            imported += 1
            if not args.quiet:
                print(f"Imported: {filepath.name} -> {new_skill.name} ({new_skill.id})")
        except Exception as e:
            print(f"Error importing {filepath.name}: {e}")

    print(f"\nImported {imported} skills from {source_dir}")
    if skipped:
        print(f"Skipped {skipped} existing skills (use --force to overwrite)")


def run_skills_audit(skills_manager: SkillsManager, args):
    """Audit skills and recommend improvements."""
    from ..skills.audit import SkillAuditor

    auditor = SkillAuditor(skills_manager.store)
    result = auditor.audit(brief=args.brief)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        recs = result["recommendations"]
        summary = result["summary"]

        if not recs:
            print("All skills are healthy. No recommendations.")
            return

        print(f"\nSkill Audit Results")
        print("=" * 50)
        print(f"Total skills: {summary['total_skills']}")
        print(f"Needs improvement: {summary['needs_improvement']}")
        print(f"Suggested new: {summary['suggested_new']}")
        print(f"Stale: {summary['stale']}")

        print(f"\nRecommendations:")
        for i, rec in enumerate(recs, 1):
            priority_marker = {"high": "!!!", "medium": "!!", "low": "!"}.get(rec["priority"], "")
            rec_type = rec["type"].upper()
            if rec["type"] == "create":
                print(f"  {i}. [{rec_type}] {priority_marker} {rec['pattern']}")
            else:
                print(f"  {i}. [{rec_type}] {priority_marker} {rec.get('skill_name', 'unknown')}")
            print(f"     Reason: {rec['reason']}")


def run_skills_ingest(skills_manager: SkillsManager, args):
    """Ingest skill-creator benchmark results."""
    from ..skills.ingest import BenchmarkIngestor

    ingestor = BenchmarkIngestor(skills_manager.store)
    result = ingestor.ingest(
        workspace_path=args.benchmark,
        skill_name=args.skill_name,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)

        print(f"\nBenchmark Ingested")
        print("=" * 30)
        print(f"Skill: {result['skill_name']}")
        print(f"Skill ID: {result['skill_id'] or 'not found in DB'}")
        print(f"Source: {result['source']}")
        print(f"Effectiveness: {result['metrics']['effectiveness']:.3f}")
        print(f"Error Rate: {result['metrics']['error_rate']:.3f}")
        print(f"Execution Time: {result['metrics']['execution_time']:.0f}ms")


def run_skills_track(skills_manager: SkillsManager, args):
    """Track a skill usage event during a session."""
    from datetime import date as date_mod

    session_date = args.date or date_mod.today().isoformat()

    try:
        skills_manager.store.track_event(
            session_date=session_date,
            skill_name=args.skill_name,
            event_type=args.event,
            description=args.description,
            step_ref=args.step,
        )
        print(f"Tracked: {args.event} for {args.skill_name}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def run_skills_track_summary(skills_manager: SkillsManager, args):
    """Summarize tracked events for a session."""
    from datetime import date as date_mod

    session_date = args.date or date_mod.today().isoformat()
    summary = skills_manager.store.get_track_summary(session_date)

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        if not summary["skills_used"] and not summary["skills_ok"]:
            print(f"No skill events tracked for {session_date}.")
            return

        if summary["skills_used"]:
            print(f"\nSkills needing improvement:")
            for s in summary["skills_used"]:
                print(f"  [{s['skill_name']}] {s['reason']}")
                for e in s["events"]:
                    step = f" ({e['step_ref']})" if e["step_ref"] else ""
                    print(f"    - {e['event_type']}{step}: {e['description']}")

        if summary["skills_ok"]:
            print(f"\nSkills OK (no issues): {', '.join(summary['skills_ok'])}")


def run_skills_suggest(skills_manager: SkillsManager, args):
    """Record a skill creation suggestion."""
    suggestion_id = skills_manager.store.add_suggestion(
        context=args.context,
        description=args.description,
    )
    print(f"Suggestion #{suggestion_id}: {args.context}")


def run_skills_suggest_summary(skills_manager: SkillsManager, args):
    """Show suggestion clusters ready for promotion."""
    min_count = args.min_count if hasattr(args, 'min_count') else 2
    clusters = skills_manager.store.get_suggestion_summary(min_count)

    if args.json:
        print(json.dumps(clusters, indent=2, default=str))
        return

    if not clusters:
        print("No recurring suggestions found.")
        return

    print(f"\nRecurring skill suggestions (>= {min_count} occurrences):\n")
    for c in clusters:
        print(f"  [{c['count']}x] {c['context']}")
        print(f"       {c['description']}")
        print(f"       first: {c['first_seen']}  last: {c['last_seen']}")
        print()


def _display_width(s: str) -> int:
    """Calculate terminal display width accounting for East Asian characters."""
    import unicodedata
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ('F', 'W') else 1
    return width


def _truncate_to_width(s: str, max_width: int) -> str:
    """Truncate string to fit within max_width terminal columns."""
    import unicodedata
    width = 0
    result = []
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        ch_width = 2 if eaw in ('F', 'W') else 1
        if width + ch_width > max_width:
            break
        result.append(ch)
        width += ch_width
    # Pad with spaces to fill max_width
    text = ''.join(result)
    padding = max_width - _display_width(text)
    return text + ' ' * padding


def run_skills_check_updates(config: CogMemConfig, args):
    """Check for updates on external skill sources and plugins."""
    import subprocess
    from datetime import datetime

    cache_path = Path(config._base_dir) / "memory" / "skill-updates.json"
    results: dict[str, Any] = {"checked_at": datetime.now().isoformat(), "sources": {}}

    # Check git-based sources under ~/.claude/skills/
    skills_dir = Path.home() / ".claude" / "skills"
    if skills_dir.exists():
        for entry in skills_dir.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            git_dir = entry / ".git"
            if not git_dir.exists():
                continue
            try:
                subprocess.run(
                    ["git", "fetch", "-q"],
                    cwd=str(entry), capture_output=True, timeout=15,
                )
                local = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(entry), capture_output=True, text=True, timeout=5,
                    encoding="utf-8", errors="replace",
                ).stdout.strip()
                # Try main, then master
                remote = ""
                for branch in ("origin/main", "origin/master"):
                    r = subprocess.run(
                        ["git", "rev-parse", branch],
                        cwd=str(entry), capture_output=True, text=True, timeout=5,
                        encoding="utf-8", errors="replace",
                    )
                    if r.returncode == 0:
                        remote = r.stdout.strip()
                        break
                # Get version from package.json if exists
                pkg = entry / "package.json"
                version = ""
                if pkg.exists():
                    try:
                        version = json.loads(pkg.read_text())["version"]
                    except Exception:
                        pass
                behind = 0
                if remote and local != remote:
                    r = subprocess.run(
                        ["git", "rev-list", "--count", f"{local}..{remote}"],
                        cwd=str(entry), capture_output=True, text=True, timeout=5,
                        encoding="utf-8", errors="replace",
                    )
                    if r.returncode == 0:
                        behind = int(r.stdout.strip())

                results["sources"][entry.name] = {
                    "type": "git",
                    "version": version,
                    "local_sha": local[:8],
                    "remote_sha": remote[:8] if remote else "",
                    "up_to_date": local == remote if remote else True,
                    "behind": behind,
                }
            except (subprocess.TimeoutExpired, Exception) as e:
                results["sources"][entry.name] = {
                    "type": "git",
                    "error": str(e),
                    "up_to_date": True,
                }

    # Build marketplace version index
    marketplace_versions: dict[str, str] = {}  # plugin_name -> latest version
    marketplaces_dir = Path.home() / ".claude" / "plugins" / "marketplaces"
    if marketplaces_dir.exists():
        # superpowers-marketplace style (marketplace.json with plugins array)
        for mp_dir in marketplaces_dir.iterdir():
            mj = mp_dir / ".claude-plugin" / "marketplace.json"
            if mj.exists():
                try:
                    md = json.loads(mj.read_text())
                    for p in md.get("plugins", []):
                        v = p.get("version", "")
                        if v:
                            marketplace_versions[p["name"]] = v
                except Exception:
                    pass
            # claude-plugins-official style (per-plugin plugin.json)
            plugins_dir = mp_dir / "plugins"
            if plugins_dir.exists():
                for pdir in plugins_dir.iterdir():
                    pj = pdir / ".claude-plugin" / "plugin.json"
                    if pj.exists():
                        try:
                            pd = json.loads(pj.read_text())
                            v = pd.get("version", "")
                            if v:
                                marketplace_versions[pdir.name] = v
                        except Exception:
                            pass

    # Check plugins
    plugins_json = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if plugins_json.exists():
        try:
            data = json.loads(plugins_json.read_text())
            for key, installs in data.get("plugins", {}).items():
                name = key.split("@")[0]
                for inst in installs:
                    installed_ver = inst.get("version", "")
                    latest_ver = marketplace_versions.get(name, "")
                    up_to_date = True
                    if installed_ver and latest_ver and installed_ver != latest_ver:
                        try:
                            from packaging.version import Version
                            up_to_date = Version(installed_ver) >= Version(latest_ver)
                        except Exception:
                            up_to_date = False
                    results["sources"][f"plugin:{name}"] = {
                        "type": "plugin",
                        "version": installed_ver,
                        "latest_version": latest_ver,
                        "up_to_date": up_to_date,
                    }
        except Exception:
            pass

    cache_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    if getattr(args, 'json', False):
        print(json.dumps(results, indent=2))
    else:
        for name, info in results["sources"].items():
            if info.get("error"):
                status = "error"
            elif info["up_to_date"]:
                status = "up to date"
            else:
                if info["type"] == "git":
                    status = f"{info['behind']} commits behind"
                else:
                    try:
                        from packaging.version import Version
                        if Version(info['version']) > Version(info.get('latest_version', '0')):
                            status = f"ahead of marketplace ({info.get('latest_version', '?')})"
                        else:
                            status = f"{info['version']} -> {info.get('latest_version', '?')}"
                    except Exception:
                        status = f"{info['version']} -> {info.get('latest_version', '?')}"
            ver = f" v{info['version']}" if info.get("version") else ""
            print(f"  {name}{ver}: {status}")


def run_skills_review(skills_manager: SkillsManager, args):
    """Full skill health review with recommendations."""
    from ..skills.audit import SkillAuditor

    auditor = SkillAuditor(skills_manager.store)
    result = auditor.review()

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    summary = result["summary"]
    skills = result["skills"]
    recs = result["recommendations"]

    print(f"\nSkill Health Review")
    print("=" * 60)
    print(f"Total: {summary['total_skills']}  "
          f"Healthy: {summary['healthy']}  "
          f"Critical: {summary['critical']}  "
          f"New: {summary['new']}")
    print()

    # Status indicators
    status_icon = {
        "healthy": "[OK]",
        "needs_attention": "[!!]",
        "critical": "[XX]",
        "new": "[  ]",
    }
    trend_icon = {
        "improving": "^",
        "declining": "v",
        "stable": "-",
    }

    name_col = 28
    if skills:
        print(f"{'Status':<8} {'Name':<{name_col}} {'Eff':>5} {'Trend':>5} {'Exec':>5} {'Ver':>4}")
        print("-" * 60)
        for s in skills:
            icon = status_icon.get(s["status"], "?")
            arrow = trend_icon.get(s["trend"], "-")
            name = _truncate_to_width(s['name'], name_col)
            print(f"{icon:<8} {name} {s['effectiveness']:>5.2f} {arrow:>5} {s['executions']:>5} {s['version']:>4}")
        print()

    if recs:
        print(f"Recommendations ({len(recs)}):")
        print("-" * 60)
        for i, rec in enumerate(recs, 1):
            priority = {"high": "!!!", "medium": "!!", "low": "!"}.get(rec["priority"], "")
            if rec["type"] == "create":
                print(f"  {i}. [CREATE] {priority} {rec['pattern']}")
            elif rec["type"] == "improve":
                print(f"  {i}. [IMPROVE] {priority} {rec.get('skill_name', '?')}")
            elif rec["type"] == "stale":
                print(f"  {i}. [STALE] {priority} {rec.get('skill_name', '?')}")
            print(f"     {rec['reason']}")
        print()
        print("Run /skill-improve <name> to start improvement loop.")
    else:
        print("All skills are healthy. No recommendations.")