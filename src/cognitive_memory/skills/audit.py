"""Skill audit system for detecting improvement opportunities."""

from __future__ import annotations

from typing import Dict, List

from .store import SkillsStore


class SkillAuditor:
    """Analyzes skill health and recommends improvements.

    Detects:
    - Low effectiveness skills needing improvement
    - Declining effectiveness trends
    - Unmatched task patterns that could become new skills
    - Stale/unused skills
    """

    def __init__(self, store: SkillsStore):
        self.store = store

    def audit(self, brief: bool = False) -> Dict:
        """Run skill audit and return recommendations.

        Args:
            brief: If True, skip slow scans (for Session Init).

        Returns:
            Dict with recommendations and summary.
        """
        recommendations: List[Dict] = []

        # Always run: fast DB queries
        recommendations.extend(self._check_low_effectiveness())
        recommendations.extend(self._check_declining_skills())

        if not brief:
            recommendations.extend(self._check_unmatched_patterns())
            recommendations.extend(self._check_stale_skills())

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 9))

        return {
            "recommendations": recommendations,
            "summary": {
                "total_skills": self._count_skills(),
                "needs_improvement": sum(
                    1 for r in recommendations if r["type"] == "improve"
                ),
                "suggested_new": sum(
                    1 for r in recommendations if r["type"] == "create"
                ),
                "stale": sum(
                    1 for r in recommendations if r["type"] == "stale"
                ),
            },
        }

    def _check_low_effectiveness(self) -> List[Dict]:
        """Find skills with low effectiveness."""
        results = []
        for skill in self.store.get_low_effectiveness_skills(
            threshold=0.5, min_executions=3
        ):
            results.append({
                "type": "improve",
                "skill_name": skill["name"],
                "skill_id": skill["id"],
                "reason": (
                    f"effectiveness {skill['average_effectiveness']:.2f} "
                    f"over {skill['total_executions']} executions"
                ),
                "priority": "high"
                if skill["average_effectiveness"] < 0.3
                else "medium",
            })
        return results

    def _check_declining_skills(self) -> List[Dict]:
        """Find skills with declining effectiveness trend."""
        results = []
        all_skills = self.store.load_all_skills()
        for category_skills in all_skills.values():
            for skill in category_skills:
                usage_log = self.store.get_recent_usage_log(skill.id, limit=3)
                if len(usage_log) < 3:
                    continue
                # Check if all 3 recent entries show declining effectiveness
                effs = [
                    e["effectiveness"]
                    for e in usage_log
                    if e["effectiveness"] is not None
                ]
                if len(effs) < 3:
                    continue
                # usage_log is DESC order, so effs[0] is most recent
                if effs[0] < effs[1] < effs[2]:
                    results.append({
                        "type": "improve",
                        "skill_name": skill.name,
                        "skill_id": skill.id,
                        "reason": (
                            f"declining trend: "
                            f"{effs[2]:.2f} → {effs[1]:.2f} → {effs[0]:.2f}"
                        ),
                        "priority": "medium",
                    })
        return results

    def _check_unmatched_patterns(self) -> List[Dict]:
        """Find repeated task patterns without matching skills."""
        results = []
        for pattern in self.store.get_unmatched_patterns(min_frequency=3):
            results.append({
                "type": "create",
                "pattern": pattern["context"],
                "frequency": pattern["frequency"],
                "avg_effectiveness": pattern["avg_effectiveness"],
                "last_seen": pattern["last_seen"],
                "reason": (
                    f"repeated {pattern['frequency']} times with no matching skill"
                ),
                "priority": "medium"
                if pattern["frequency"] < 5
                else "high",
            })
        return results

    def _check_stale_skills(self) -> List[Dict]:
        """Find skills unused for a long time."""
        results = []
        for skill in self.store.get_stale_skills(days=60):
            results.append({
                "type": "stale",
                "skill_name": skill["name"],
                "skill_id": skill["id"],
                "last_used": skill["last_used_at"],
                "reason": f"unused since {skill['last_used_at'][:10]}",
                "priority": "low",
            })
        return results

    def review(self) -> Dict:
        """Full skill review: health report + audit recommendations.

        Returns a comprehensive review including per-skill health status
        and actionable recommendations.
        """
        audit_result = self.audit(brief=False)
        all_skills = self.store.load_all_skills()

        # Build per-skill health report
        skill_reports = []
        for category_skills in all_skills.values():
            for skill in category_skills:
                usage_log = self.store.get_recent_usage_log(skill.id, limit=5)
                recent_effs = [
                    e["effectiveness"]
                    for e in usage_log
                    if e["effectiveness"] is not None
                ]

                # Determine health status
                eff = skill.usage_stats.average_effectiveness
                execs = skill.usage_stats.total_executions
                if execs < 3:
                    status = "new"
                elif eff >= 0.7:
                    status = "healthy"
                elif eff >= 0.5:
                    status = "needs_attention"
                else:
                    status = "critical"

                # Detect trend
                trend = "stable"
                if len(recent_effs) >= 3:
                    if recent_effs[0] < recent_effs[1] < recent_effs[2]:
                        trend = "declining"
                    elif recent_effs[0] > recent_effs[1] > recent_effs[2]:
                        trend = "improving"

                skill_reports.append({
                    "name": skill.name,
                    "id": skill.id,
                    "category": skill.category,
                    "effectiveness": eff,
                    "executions": execs,
                    "version": skill.version,
                    "last_used": skill.usage_stats.last_used_at,
                    "status": status,
                    "trend": trend,
                    "recent_effectiveness": recent_effs[:5],
                })

        # Sort: critical first, then by effectiveness ascending
        status_order = {"critical": 0, "needs_attention": 1, "new": 2, "healthy": 3}
        skill_reports.sort(key=lambda r: (status_order.get(r["status"], 9), r["effectiveness"]))

        return {
            "skills": skill_reports,
            "recommendations": audit_result["recommendations"],
            "summary": {
                **audit_result["summary"],
                "healthy": sum(1 for s in skill_reports if s["status"] == "healthy"),
                "critical": sum(1 for s in skill_reports if s["status"] == "critical"),
                "new": sum(1 for s in skill_reports if s["status"] == "new"),
            },
        }

    def _count_skills(self) -> int:
        """Count total skills in DB."""
        all_skills = self.store.load_all_skills()
        return sum(len(skills) for skills in all_skills.values())
