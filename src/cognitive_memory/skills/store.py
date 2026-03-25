"""Skills storage and retrieval system integrated with cognitive memory."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from ..config import CogMemConfig
from .types import Skill, SkillCategory, SKILL_CATEGORIES


class SkillsStore:
    """Storage layer for skills, integrated with cognitive memory system."""

    def __init__(self, config: CogMemConfig):
        self.config = config
        self.skills_dir = Path(config._base_dir) / "memory" / "skills"
        self.db_path = Path(config._base_dir) / "memory" / "skills.db"
        self._init_storage()

    def _init_storage(self) -> None:
        """Initialize skills storage directories and database."""
        # Create skills directory structure
        for category in SKILL_CATEGORIES:
            category_path = self.skills_dir / category
            category_path.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite database for skill metadata and search
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database for skill metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    execution_pattern TEXT NOT NULL,
                    average_effectiveness REAL NOT NULL,
                    total_executions INTEGER NOT NULL,
                    successful_executions INTEGER NOT NULL,
                    last_used_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    file_path TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_skills_category
                ON skills(category)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_skills_effectiveness
                ON skills(average_effectiveness DESC)
            """)

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS skills_search USING fts5(
                    skill_id UNINDEXED,
                    name,
                    description,
                    execution_pattern
                )
            """)

    def save_skill(self, skill: Skill) -> None:
        """Save skill to both file system and database."""
        # Save to file system
        category_path = self.skills_dir / skill.category
        file_path = category_path / f"{skill.id}.json"

        skill_dict = {
            "id": skill.id,
            "name": skill.name,
            "category": skill.category,
            "description": skill.description,
            "execution_pattern": skill.execution_pattern,
            "success_metrics": [
                {
                    "name": m.name,
                    "description": m.description,
                    "measurement_method": m.measurement_method,
                    "target_value": m.target_value,
                    "current_value": m.current_value,
                }
                for m in skill.success_metrics
            ],
            "improvement_history": [
                {
                    "timestamp": r.timestamp,
                    "description": r.description,
                    "before_value": r.before_value,
                    "after_value": r.after_value,
                    "effectiveness_gain": r.effectiveness_gain,
                }
                for r in skill.improvement_history
            ],
            "usage_stats": {
                "total_executions": skill.usage_stats.total_executions,
                "successful_executions": skill.usage_stats.successful_executions,
                "average_effectiveness": skill.usage_stats.average_effectiveness,
                "last_used_at": skill.usage_stats.last_used_at,
                "frequency": skill.usage_stats.frequency,
            },
            "created_at": skill.created_at,
            "updated_at": skill.updated_at,
            "version": skill.version,
        }

        with open(file_path, 'w') as f:
            json.dump(skill_dict, f, indent=2)

        # Save to database for quick search
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO skills (
                    id, name, category, description, execution_pattern,
                    average_effectiveness, total_executions, successful_executions,
                    last_used_at, created_at, updated_at, version, file_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                skill.id,
                skill.name,
                skill.category,
                skill.description,
                skill.execution_pattern,
                skill.usage_stats.average_effectiveness,
                skill.usage_stats.total_executions,
                skill.usage_stats.successful_executions,
                skill.usage_stats.last_used_at,
                skill.created_at,
                skill.updated_at,
                skill.version,
                str(file_path)
            ))

            # Update FTS index
            conn.execute("""
                INSERT OR REPLACE INTO skills_search (skill_id, name, description, execution_pattern)
                VALUES (?, ?, ?, ?)
            """, (skill.id, skill.name, skill.description, skill.execution_pattern))

    def load_skill(self, category: SkillCategory, skill_id: str) -> Optional[Skill]:
        """Load skill from file system."""
        file_path = self.skills_dir / category / f"{skill_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)

            return self._skill_from_dict(data)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error loading skill {skill_id}: {e}")
            return None

    def load_all_skills(self) -> Dict[SkillCategory, List[Skill]]:
        """Load all skills grouped by category."""
        skills_map: Dict[SkillCategory, List[Skill]] = {}

        for category in SKILL_CATEGORIES:
            category_path = self.skills_dir / category
            skills: List[Skill] = []

            if category_path.exists():
                for file_path in category_path.glob("*.json"):
                    skill_id = file_path.stem
                    skill = self.load_skill(category, skill_id)
                    if skill:
                        skills.append(skill)

            skills_map[category] = skills

        return skills_map

    def _sanitize_fts_query(self, query: str) -> str:
        """Sanitize query for FTS5 to avoid column name misinterpretation."""
        import re
        tokens = re.findall(r'[a-zA-Z0-9\u3000-\u9fff\uf900-\ufaff\uff66-\uff9f]+', query)
        if not tokens:
            return '""'
        return " OR ".join(f'"{t}"' for t in tokens[:20])

    def search_skills(
        self,
        query: str,
        category: Optional[SkillCategory] = None,
        top_k: int = 5,
        min_effectiveness: float = 0.0
    ) -> List[Skill]:
        """Search skills using FTS and semantic similarity."""
        skills = []
        safe_query = self._sanitize_fts_query(query)

        with sqlite3.connect(self.db_path) as conn:
            try:
                if category:
                    cursor = conn.execute("""
                        SELECT s.id, s.category FROM skills s
                        JOIN skills_search fs ON s.id = fs.skill_id
                        WHERE skills_search MATCH ? AND s.category = ? AND s.average_effectiveness >= ?
                        ORDER BY s.average_effectiveness DESC
                        LIMIT ?
                    """, (safe_query, category, min_effectiveness, top_k))
                else:
                    cursor = conn.execute("""
                        SELECT s.id, s.category FROM skills s
                        JOIN skills_search fs ON s.id = fs.skill_id
                        WHERE skills_search MATCH ? AND s.average_effectiveness >= ?
                        ORDER BY s.average_effectiveness DESC
                        LIMIT ?
                    """, (safe_query, min_effectiveness, top_k))

                for skill_id, skill_category in cursor.fetchall():
                    skill = self.load_skill(skill_category, skill_id)
                    if skill:
                        skills.append(skill)
            except Exception:
                pass

        return skills

    def get_top_skills(self, limit: int = 10) -> List[Skill]:
        """Get top performing skills."""
        skills = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, category FROM skills
                ORDER BY average_effectiveness DESC, total_executions DESC
                LIMIT ?
            """, (limit,))

            for skill_id, category in cursor.fetchall():
                skill = self.load_skill(category, skill_id)
                if skill:
                    skills.append(skill)

        return skills

    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get all skills in a specific category."""
        return self.load_all_skills()[category]

    def delete_skill(self, skill_id: str) -> bool:
        """Delete skill from storage."""
        # Find and delete from file system
        for category in SKILL_CATEGORIES:
            file_path = self.skills_dir / category / f"{skill_id}.json"
            if file_path.exists():
                file_path.unlink()
                break
        else:
            return False  # Skill not found

        # Delete from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
            conn.execute("DELETE FROM skills_search WHERE skill_id = ?", (skill_id,))

        return True

    def _skill_from_dict(self, data: dict) -> Skill:
        """Convert dictionary to Skill object."""
        from .types import Skill, SuccessMetric, ImprovementRecord, UsageStats

        success_metrics = [
            SuccessMetric(
                name=m["name"],
                description=m["description"],
                measurement_method=m["measurement_method"],
                target_value=m.get("target_value"),
                current_value=m.get("current_value"),
            )
            for m in data["success_metrics"]
        ]

        improvement_history = [
            ImprovementRecord(
                timestamp=r["timestamp"],
                description=r["description"],
                before_value=r.get("before_value"),
                after_value=r.get("after_value"),
                effectiveness_gain=r["effectiveness_gain"],
            )
            for r in data["improvement_history"]
        ]

        usage_stats = UsageStats(
            total_executions=data["usage_stats"]["total_executions"],
            successful_executions=data["usage_stats"]["successful_executions"],
            average_effectiveness=data["usage_stats"]["average_effectiveness"],
            last_used_at=data["usage_stats"].get("last_used_at"),
            frequency=data["usage_stats"]["frequency"],
        )

        return Skill(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            description=data["description"],
            execution_pattern=data["execution_pattern"],
            success_metrics=success_metrics,
            improvement_history=improvement_history,
            usage_stats=usage_stats,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            version=data["version"],
        )