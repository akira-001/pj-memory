"""Skills service for dashboard views."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from ...config import CogMemConfig
from ...skills.store import SkillsStore
from ...skills.audit import SkillAuditor


def get_skills_list(config: CogMemConfig) -> list:
    """Get all skills as flat list with trend info.

    Returns list of dicts:
        {id, name, category, effectiveness, total_executions, last_used_at, trend}
    trend: "up" | "down" | "flat" | "new" based on skill_usage_log last 5 entries
    """
    store = SkillsStore(config)
    all_skills = store.load_all_skills()

    result = []
    for category, skills in all_skills.items():
        for skill in skills:
            usage_log = store.get_recent_usage_log(skill.id, 5)
            effs = [
                e["effectiveness"]
                for e in usage_log
                if e["effectiveness"] is not None
            ]
            trend = _determine_trend(effs)

            result.append({
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "effectiveness": skill.usage_stats.average_effectiveness,
                "total_executions": skill.usage_stats.total_executions,
                "last_used_at": skill.usage_stats.last_used_at,
                "trend": trend,
            })

    result.sort(key=lambda s: (s["category"], s["name"]))
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
    return auditor.audit()
