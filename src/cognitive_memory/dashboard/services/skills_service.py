"""Skills service for dashboard views."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import List, Optional

from ...config import CogMemConfig
from ...skills.store import SkillsStore
from ...skills.audit import SkillAuditor

# Common locations for .claude/skills/
_CLAUDE_SKILLS_DIRS = [
    Path.home() / ".claude" / "skills",
]


def _scan_claude_skills() -> dict[str, dict]:
    """Scan .claude/skills/ directories for user's own skill metadata.

    Excludes: agency-* (marketplace), symlinks (gstack/superpowers), learned/, __pycache__
    """
    skills = {}
    for skills_dir in _CLAUDE_SKILLS_DIRS:
        if not skills_dir.exists():
            continue
        for entry in skills_dir.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            # Skip marketplace/framework skills
            if entry.name.startswith("agency-") or entry.is_symlink():
                continue
            if entry.name in ("learned", "gstack", "__pycache__"):
                continue
            skill_file = entry / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                text = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            # Parse YAML frontmatter
            fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not fm_match:
                continue
            fm = fm_match.group(1)
            name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
            desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
            if name_match:
                skill_name = name_match.group(1).strip()
                skills[skill_name] = {
                    "name": skill_name,
                    "description": desc_match.group(1).strip() if desc_match else "",
                    "path": str(skill_file),
                }
    return skills


def _get_event_stats(config: CogMemConfig) -> dict[str, dict]:
    """Get per-skill event stats from skill_session_events table."""
    db_path = Path(config._base_dir) / "memory" / "skills.db"
    if not db_path.exists():
        return {}
    stats: dict[str, dict] = {}
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT skill_name, event_type, COUNT(*) as cnt, "
            "MAX(timestamp) as last_ts "
            "FROM skill_session_events "
            "GROUP BY skill_name, event_type"
        ).fetchall()
        for r in rows:
            name = r["skill_name"]
            if name not in stats:
                stats[name] = {"total_events": 0, "last_used": None, "events_by_type": {}}
            stats[name]["total_events"] += r["cnt"]
            stats[name]["events_by_type"][r["event_type"]] = r["cnt"]
            if stats[name]["last_used"] is None or r["last_ts"] > stats[name]["last_used"]:
                stats[name]["last_used"] = r["last_ts"]
        conn.close()
    except sqlite3.Error:
        pass
    return stats


def _load_db_skills(config: CogMemConfig) -> list[dict]:
    """Load all DB skills directly from SQLite with claude_skill_name mapping.

    Reads the skills table. Adds claude_skill_name column if missing (migration).
    """
    db_path = Path(config._base_dir) / "memory" / "skills.db"
    if not db_path.exists():
        return []
    result: list[dict] = []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Migration: add claude_skill_name column if missing
        try:
            conn.execute("ALTER TABLE skills ADD COLUMN claude_skill_name TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists

        rows = conn.execute(
            "SELECT id, name, category, description, average_effectiveness, "
            "total_executions, last_used_at, version, claude_skill_name FROM skills"
        ).fetchall()
        for row in rows:
            # Get usage log for trend
            usage_rows = conn.execute(
                "SELECT effectiveness FROM skill_usage_log "
                "WHERE skill_id = ? ORDER BY timestamp DESC LIMIT 5",
                (row["id"],),
            ).fetchall()
            effs = [r["effectiveness"] for r in usage_rows if r["effectiveness"] is not None]
            result.append({
                "id": row["id"],
                "claude_skill_name": row["claude_skill_name"],
                "category": row["category"],
                "effectiveness": row["average_effectiveness"],
                "total_executions": row["total_executions"],
                "last_used_at": row["last_used_at"],
                "trend": _determine_trend(effs),
                "version": row["version"],
                "improvements": max(0, row["version"] - 1),
            })
        conn.close()
    except sqlite3.Error:
        pass
    return result


def get_skills_list(config: CogMemConfig) -> list:
    """Get skills from .claude/skills/ enriched with cogmem DB stats.

    Matching priority:
    1. DB skill id == .claude/skills/ directory name (exact)
    2. DB claude_skill_name == .claude/skills/ directory name
    """
    claude_skills = _scan_claude_skills()
    event_stats = _get_event_stats(config)
    db_skills = _load_db_skills(config)
    matched_ids: set = set()

    result = []
    for skill_name, meta in claude_skills.items():
        events = event_stats.get(skill_name, {})

        # Match: exact id, then claude_skill_name column
        db = None
        for d in db_skills:
            if d["id"] in matched_ids:
                continue
            if d["id"] == skill_name or d.get("claude_skill_name") == skill_name:
                db = d
                matched_ids.add(d["id"])
                break

        result.append({
            "id": skill_name,
            "name": skill_name,
            "summary": meta["description"],
            "description": meta["description"],
            "category": db["category"] if db else "—",
            "effectiveness": db["effectiveness"] if db else 0.0,
            "total_executions": db["total_executions"] if db else 0,
            "total_events": events.get("total_events", 0),
            "last_used_at": (db["last_used_at"] if db else None) or events.get("last_used"),
            "trend": db["trend"] if db else "new",
            "version": db["version"] if db else 1,
            "improvements": db["improvements"] if db else 0,
            "events_by_type": events.get("events_by_type", {}),
        })

    result.sort(key=lambda s: s["total_executions"], reverse=True)
    return result


def _determine_trend(effs: list) -> str:
    """Determine trend from effectiveness values (newest first)."""
    if len(effs) < 3:
        return "new"
    if len(effs) >= 5:
        is_increasing = all(effs[i] > effs[i + 1] for i in range(len(effs) - 1))
        if is_increasing:
            return "up"
        is_decreasing = all(effs[i] < effs[i + 1] for i in range(len(effs) - 1))
        if is_decreasing:
            return "down"
    return "flat"


def get_skill_detail(config: CogMemConfig, skill_id: str) -> Optional[dict]:
    """Get skill detail with usage log and events.

    Returns {skill: Skill, usage_log: list, events: list} or None.
    """
    store = SkillsStore(config)
    all_skills = store.load_all_skills()

    skill = None
    for category_skills in all_skills.values():
        for s in category_skills:
            if s.id == skill_id:
                skill = s
                break
        if skill:
            break

    if skill is None:
        return None

    usage_log = store.get_recent_usage_log(skill.id, 20)

    events: list = []
    try:
        with sqlite3.connect(store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT session_date, skill_name, event_type, description, "
                "step_ref, timestamp FROM skill_session_events "
                "WHERE skill_name = ? ORDER BY timestamp DESC",
                (skill.name,),
            ).fetchall()
            events = [dict(r) for r in rows]
    except Exception:
        pass

    return {
        "skill": skill,
        "usage_log": usage_log,
        "events": events,
    }


def get_skill_trend(config: CogMemConfig, skill_id: str) -> list:
    """Get effectiveness data points for chart.

    Returns list of {timestamp, effectiveness} from skill_usage_log.
    """
    store = SkillsStore(config)
    log = store.get_recent_usage_log(skill_id, 50)
    return [
        {"timestamp": e["timestamp"], "effectiveness": e["effectiveness"]}
        for e in reversed(log)
        if e["effectiveness"] is not None
    ]


def get_audit_results(config: CogMemConfig) -> dict:
    """Run SkillAuditor.audit() and return results."""
    store = SkillsStore(config)
    auditor = SkillAuditor(store)
    result = auditor.audit()

    # Add auto-improvement stats
    db_path = Path(config._base_dir) / "memory" / "skills.db"
    total_improvements = 0
    unresolved_events = 0
    auto_created = 0
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            row = conn.execute(
                "SELECT COUNT(*) FROM skill_session_events WHERE resolved = 1"
            ).fetchone()
            total_improvements = row[0] if row else 0
            row2 = conn.execute(
                "SELECT COUNT(*) FROM skill_session_events WHERE resolved = 0"
            ).fetchone()
            unresolved_events = row2[0] if row2 else 0
            row3 = conn.execute(
                "SELECT COUNT(DISTINCT context) FROM skill_suggestions WHERE promoted = 1"
            ).fetchone()
            auto_created = row3[0] if row3 else 0
            conn.close()
        except sqlite3.Error:
            pass
    result["summary"]["total_improvements"] = total_improvements
    result["summary"]["unresolved_events"] = unresolved_events
    result["summary"]["auto_created"] = auto_created
    # Override total_skills with .claude/skills/ count (not DB count)
    claude_skills = _scan_claude_skills()
    result["summary"]["total_skills"] = len(claude_skills)
    return result
