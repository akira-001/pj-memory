"""Ingest skill-creator benchmark results into cogmem skills DB."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .store import SkillsStore
from .types import PerformanceMetric


class BenchmarkIngestor:
    """Parses skill-creator eval/benchmark outputs and feeds metrics into cogmem.

    Supports:
    - benchmark.json (aggregated stats from skill-creator)
    - grading.json (individual eval results)
    """

    def __init__(self, store: SkillsStore):
        self.store = store

    def ingest(
        self,
        workspace_path: str,
        skill_name: str,
    ) -> Dict:
        """Ingest benchmark results from a skill-creator workspace directory.

        Args:
            workspace_path: Path to skill-creator workspace (containing benchmark.json or grading.json)
            skill_name: Name of the skill to update in cogmem DB

        Returns:
            Dict with ingestion results
        """
        workspace = Path(workspace_path)
        if not workspace.is_dir():
            return {"error": f"Directory not found: {workspace_path}"}

        # Try benchmark.json first (aggregated), then grading.json (individual)
        performance = self._parse_benchmark(workspace)
        if performance is None:
            performance = self._parse_grading(workspace)
        if performance is None:
            return {"error": "No benchmark.json or grading.json found"}

        # Find matching skill in DB
        skill_id = self._find_skill_id(skill_name)

        # Log usage with extracted metrics
        self.store.log_usage(
            context=f"skill-creator eval: {skill_name}",
            skill_id=skill_id,
            effectiveness=performance.effectiveness,
        )

        return {
            "status": "ingested",
            "skill_name": skill_name,
            "skill_id": skill_id,
            "metrics": {
                "effectiveness": performance.effectiveness,
                "error_rate": performance.error_rate,
                "execution_time": performance.execution_time,
                "user_satisfaction": performance.user_satisfaction,
            },
            "source": "benchmark.json"
            if (workspace / "benchmark.json").exists()
            else "grading.json",
        }

    def _parse_benchmark(self, workspace: Path) -> Optional[PerformanceMetric]:
        """Parse benchmark.json from skill-creator."""
        benchmark_path = workspace / "benchmark.json"
        if not benchmark_path.exists():
            return None

        try:
            data = json.loads(benchmark_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        # Extract from run_summary.with_skill
        run_summary = data.get("run_summary", {})
        with_skill = run_summary.get("with_skill", {})

        pass_rate = with_skill.get("pass_rate", {})
        time_stats = with_skill.get("time_seconds", {})

        effectiveness = pass_rate.get("mean", 0.5)
        execution_time = time_stats.get("mean", 1.0) * 1000  # sec → ms

        # Estimate error_rate from runs if available
        runs = data.get("runs", [])
        total_errors = sum(r.get("result", {}).get("errors", 0) for r in runs)
        total_tool_calls = sum(
            r.get("result", {}).get("tool_calls", 1) for r in runs
        )
        error_rate = (
            total_errors / total_tool_calls if total_tool_calls > 0 else 0.0
        )

        return PerformanceMetric(
            effectiveness=effectiveness,
            user_satisfaction=effectiveness,  # proxy
            execution_time=execution_time,
            error_rate=error_rate,
        )

    def _parse_grading(self, workspace: Path) -> Optional[PerformanceMetric]:
        """Parse grading.json from skill-creator."""
        grading_path = workspace / "grading.json"
        if not grading_path.exists():
            return None

        try:
            data = json.loads(grading_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        summary = data.get("summary", {})
        pass_rate = summary.get("pass_rate", 0.5)

        timing = data.get("timing", {})
        execution_time = timing.get("total_seconds", 1.0) * 1000

        exec_metrics = data.get("execution_metrics", {})
        errors = exec_metrics.get("errors", 0)
        tool_calls = exec_metrics.get("tool_calls", 1)
        error_rate = errors / tool_calls if tool_calls > 0 else 0.0

        return PerformanceMetric(
            effectiveness=pass_rate,
            user_satisfaction=pass_rate,
            execution_time=execution_time,
            error_rate=error_rate,
        )

    def _find_skill_id(self, skill_name: str) -> Optional[str]:
        """Find skill ID by name in the DB."""
        all_skills = self.store.load_all_skills()
        name_lower = skill_name.lower().replace("-", " ").replace("_", " ")
        for category_skills in all_skills.values():
            for skill in category_skills:
                if skill.name.lower().replace("-", " ").replace("_", " ") == name_lower:
                    return skill.id
        return None
