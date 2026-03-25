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
    lines.append(f"# {skill.name}")
    lines.append("")
    lines.append(f"*Category: {skill.category} | Effectiveness: {skill.usage_stats.average_effectiveness:.2f} | Version: {skill.version}*")
    lines.append(f"*Skill ID: {skill.id}*")
    lines.append("")
    lines.append("## トリガー")
    for line in skill.description.split(". "):
        line = line.strip()
        if line:
            lines.append(f"- {line}")
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
    section_lines = {"triggers": [], "steps": [], "description": []}

    for line in lines:
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