"""Skills storage and retrieval system integrated with cognitive memory."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config import CogMemConfig
from ..scoring import cosine_sim, normalize
from .types import Skill, SkillCategory, SKILL_CATEGORIES


class SkillsStore:
    """Storage layer for skills, integrated with cognitive memory system."""

    def __init__(self, config: CogMemConfig):
        self.config = config
        self.skills_dir = Path(config._base_dir) / "memory" / "skills"
        self.db_path = Path(config._base_dir) / "memory" / "skills.db"
        self._embedder = None
        self._init_storage()

    @property
    def embedder(self):
        """Lazy-init Ollama embedder from config."""
        if self._embedder is None:
            from ..embeddings.ollama import OllamaEmbedding
            self._embedder = OllamaEmbedding(
                model=self.config.embedding_model,
                url=self.config.embedding_url,
                timeout=self.config.embedding_timeout,
            )
        return self._embedder

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

            # Add embedding column if missing (migration for existing DBs)
            try:
                conn.execute("ALTER TABLE skills ADD COLUMN embedding TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists

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
                    name,
                    description,
                    execution_pattern,
                    content='skills',
                    content_rowid='rowid'
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context TEXT NOT NULL,
                    skill_id TEXT,
                    effectiveness REAL,
                    timestamp TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    step_ref TEXT,
                    timestamp TEXT NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0
                )
            """)

            # Migration: add resolved column if missing
            try:
                conn.execute("ALTER TABLE skill_session_events ADD COLUMN resolved INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column already exists

            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context TEXT NOT NULL,
                    description TEXT NOT NULL,
                    session_date TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    promoted INTEGER NOT NULL DEFAULT 0
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

        # Generate embedding for semantic search
        embed_text = f"{skill.name} {skill.description} {skill.execution_pattern}"
        vec = self.embedder.embed(embed_text)
        embedding_json = json.dumps(vec) if vec else None

        # Save to database for quick search
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO skills (
                    id, name, category, description, execution_pattern,
                    average_effectiveness, total_executions, successful_executions,
                    last_used_at, created_at, updated_at, version, file_path,
                    embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                str(file_path),
                embedding_json,
            ))

            # Update FTS index (content-sync triggers handle this automatically
            # for external content tables, but we rebuild to be safe)
            conn.execute("INSERT INTO skills_search(skills_search) VALUES('rebuild')")

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
        """Search skills using vector similarity (primary) with FTS5 fallback."""
        results = self.search_skills_scored(query, category, top_k, min_effectiveness)
        return [skill for skill, _score in results]

    def search_skills_scored(
        self,
        query: str,
        category: Optional[SkillCategory] = None,
        top_k: int = 5,
        min_effectiveness: float = 0.0
    ) -> List[Tuple[Skill, float]]:
        """Search skills returning (skill, similarity_score) pairs."""
        # Try vector search first
        results = self._vector_search_scored(query, category, top_k, min_effectiveness)
        if results:
            return results

        # Fallback to FTS5 (no scores available, use 0.5 default)
        fts_skills = self._fts_search(query, category, top_k, min_effectiveness)
        return [(s, 0.5) for s in fts_skills]

    def _vector_search_scored(
        self,
        query: str,
        category: Optional[SkillCategory],
        top_k: int,
        min_effectiveness: float,
    ) -> List[Tuple[Skill, float]]:
        """Search skills using Ollama embedding cosine similarity."""
        query_vec = self.embedder.embed(query)
        if not query_vec:
            return []
        query_vec = normalize(query_vec)

        scored: List[Tuple[float, str, str]] = []
        with sqlite3.connect(self.db_path) as conn:
            sql = "SELECT id, category, embedding, average_effectiveness FROM skills"
            params: list = []
            conditions = []
            if category:
                conditions.append("category = ?")
                params.append(category)
            if min_effectiveness > 0:
                conditions.append("average_effectiveness >= ?")
                params.append(min_effectiveness)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            for row in conn.execute(sql, params):
                if not row[2]:  # no embedding
                    continue
                skill_vec = json.loads(row[2])
                sim = cosine_sim(query_vec, skill_vec)
                scored.append((sim, row[0], row[1]))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for sim, skill_id, skill_category in scored[:top_k]:
            if sim < 0.3:  # relevance threshold
                break
            skill = self.load_skill(skill_category, skill_id)
            if skill:
                results.append((skill, sim))
        return results

    def _fts_search(
        self,
        query: str,
        category: Optional[SkillCategory],
        top_k: int,
        min_effectiveness: float,
    ) -> List[Skill]:
        """Fallback FTS5 search."""
        skills = []
        safe_query = self._sanitize_fts_query(query)

        with sqlite3.connect(self.db_path) as conn:
            try:
                if category:
                    cursor = conn.execute("""
                        SELECT s.id, s.category FROM skills s
                        JOIN skills_search fs ON s.rowid = fs.rowid
                        WHERE skills_search MATCH ? AND s.category = ? AND s.average_effectiveness >= ?
                        ORDER BY s.average_effectiveness DESC
                        LIMIT ?
                    """, (safe_query, category, min_effectiveness, top_k))
                else:
                    cursor = conn.execute("""
                        SELECT s.id, s.category FROM skills s
                        JOIN skills_search fs ON s.rowid = fs.rowid
                        WHERE skills_search MATCH ? AND s.average_effectiveness >= ?
                        ORDER BY s.average_effectiveness DESC
                        LIMIT ?
                    """, (safe_query, min_effectiveness, top_k))

                for skill_id, skill_category in cursor.fetchall():
                    skill = self.load_skill(skill_category, skill_id)
                    if skill:
                        skills.append(skill)
            except Exception as e:
                import sys
                print(f"FTS5 search error: {e}", file=sys.stderr)

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
            conn.execute("INSERT INTO skills_search(skills_search) VALUES('rebuild')")

        return True

    def log_usage(
        self,
        context: str,
        skill_id: Optional[str],
        effectiveness: Optional[float],
    ) -> None:
        """Log a skill usage event for pattern detection."""
        from datetime import datetime

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO skill_usage_log (context, skill_id, effectiveness, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (context, skill_id, effectiveness, datetime.now().isoformat()),
            )

    def get_low_effectiveness_skills(
        self, threshold: float = 0.5, min_executions: int = 3
    ) -> List[dict]:
        """Get skills with low effectiveness."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, name, category, average_effectiveness, total_executions, "
                "last_used_at, file_path FROM skills "
                "WHERE average_effectiveness < ? AND total_executions >= ? "
                "ORDER BY average_effectiveness ASC",
                (threshold, min_executions),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stale_skills(self, days: int = 60) -> List[dict]:
        """Get skills unused for more than N days."""
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, name, category, average_effectiveness, total_executions, "
                "last_used_at FROM skills "
                "WHERE last_used_at IS NOT NULL AND last_used_at < ? "
                "ORDER BY last_used_at ASC",
                (cutoff,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_unmatched_patterns(self, min_frequency: int = 3) -> List[dict]:
        """Get task patterns that have no matching skill (repeated N+ times)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT context, COUNT(*) as frequency, "
                "AVG(effectiveness) as avg_effectiveness, "
                "MAX(timestamp) as last_seen "
                "FROM skill_usage_log "
                "WHERE skill_id IS NULL "
                "GROUP BY context HAVING COUNT(*) >= ? "
                "ORDER BY COUNT(*) DESC",
                (min_frequency,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_usage_log(
        self, skill_id: str, limit: int = 10
    ) -> List[dict]:
        """Get recent usage log entries for a skill."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT context, effectiveness, timestamp "
                "FROM skill_usage_log "
                "WHERE skill_id = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (skill_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Skill Session Event Tracking ---

    VALID_EVENT_TYPES = {
        "skill_start", "skill_end",
        "extra_step", "skipped_step", "error_recovery", "user_correction",
    }

    def track_event(
        self,
        session_date: str,
        skill_name: str,
        event_type: str,
        description: str,
        step_ref: Optional[str] = None,
    ) -> None:
        """Record a skill usage event during a session."""
        if event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{event_type}'. "
                f"Must be one of: {', '.join(sorted(self.VALID_EVENT_TYPES))}"
            )
        from datetime import datetime

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO skill_session_events "
                "(session_date, skill_name, event_type, description, step_ref, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (session_date, skill_name, event_type, description, step_ref,
                 datetime.now().isoformat()),
            )

    def get_session_events(self, session_date: str) -> List[dict]:
        """Get all skill events for a session date."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT skill_name, event_type, description, step_ref, timestamp "
                "FROM skill_session_events "
                "WHERE session_date = ? "
                "ORDER BY timestamp ASC",
                (session_date,),
            ).fetchall()
            return [dict(r) for r in rows]

    def resolve_events(self, skill_name: str, increment_version: bool = True) -> int:
        """Mark all unresolved events for a skill as resolved.

        Called after SKILL.md is actually edited. Increments skill version
        only when increment_version=True (auto-improvement). User-directed
        corrections should pass increment_version=False.
        Returns count of resolved events.
        """
        from datetime import datetime

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE skill_session_events SET resolved = 1 "
                "WHERE skill_name = ? AND resolved = 0",
                (skill_name,),
            )
            resolved_count = cursor.rowcount

            if resolved_count > 0 and increment_version:
                # Increment version — skill was auto-improved
                conn.execute(
                    "UPDATE skills SET version = version + 1, updated_at = ? "
                    "WHERE name = ?",
                    (datetime.now().isoformat(), skill_name),
                )

            return resolved_count

    def add_suggestion(self, context: str, description: str) -> int:
        """Record a skill creation suggestion.

        Called by the agent mid-session when it notices a repeatable pattern
        that isn't yet a skill.
        Returns the suggestion id.
        """
        from datetime import datetime, date as date_mod

        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO skill_suggestions "
                "(context, description, session_date, timestamp, promoted) "
                "VALUES (?, ?, ?, ?, 0)",
                (context, description, date_mod.today().isoformat(),
                 now.isoformat()),
            )
            return cursor.lastrowid

    def get_suggestion_summary(self, min_count: int = 2) -> list:
        """Get suggestion clusters that appear min_count+ times.

        Groups by similar context (exact match on context field).
        Returns list of {context, description, count, first_seen, last_seen}.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT context, description, COUNT(*) as cnt, "
                "MIN(session_date) as first_seen, MAX(session_date) as last_seen "
                "FROM skill_suggestions WHERE promoted = 0 "
                "GROUP BY context HAVING cnt >= ? "
                "ORDER BY cnt DESC",
                (min_count,),
            ).fetchall()
            return [dict(r) for r in rows]

    def promote_suggestion(self, context: str) -> int:
        """Mark suggestions as promoted (skill was created).

        Returns count of promoted rows.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE skill_suggestions SET promoted = 1 "
                "WHERE context = ? AND promoted = 0",
                (context,),
            )
            return cursor.rowcount

    def dismiss_suggestion(self, context: str) -> int:
        """Mark suggestions as dismissed (user rejected).

        Sets promoted = -1 so they no longer appear in suggest-summary.
        Returns count of dismissed rows.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE skill_suggestions SET promoted = -1 "
                "WHERE context = ? AND promoted = 0",
                (context,),
            )
            return cursor.rowcount

    def get_track_summary(self, session_date: str) -> dict:
        """Get track summary with improvement recommendations for a session."""
        # Get ALL unresolved events regardless of date
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT skill_name, event_type, description, step_ref, timestamp "
                "FROM skill_session_events "
                "WHERE resolved = 0 "
                "ORDER BY timestamp ASC",
            ).fetchall()
            events = [dict(r) for r in rows]

        # Group events by skill
        skills_events: dict = {}
        for e in events:
            name = e["skill_name"]
            if name not in skills_events:
                skills_events[name] = []
            skills_events[name].append(e)

        skills_used = []
        skills_ok = []

        for skill_name, skill_events in skills_events.items():
            # Filter out lifecycle events for improvement judgment
            action_events = [
                e for e in skill_events
                if e["event_type"] not in ("skill_start", "skill_end")
            ]
            needs, reason = self._needs_improvement(action_events)
            entry = {
                "skill_name": skill_name,
                "events": action_events,
                "needs_improvement": needs,
                "reason": reason,
            }
            if needs:
                skills_used.append(entry)
            else:
                skills_ok.append(skill_name)

        return {
            "date": session_date,
            "skills_used": skills_used,
            "skills_ok": skills_ok,
        }

    # Default file-pattern → skill mappings for gap detection
    _DEFAULT_SKILL_TRIGGERS = [
        {"pattern": ".claude/skills/**/SKILL.md", "skills": ["skill-improve"]},
        {"pattern": "memory/logs/**", "skills": ["live-logging"]},
    ]

    # Keywords indicating a situational/transient event (not worth codifying)
    _SITUATIONAL_KEYWORDS = [
        "タイムアウト", "timeout", "一時的", "transient", "retry",
        "ネットワーク", "network", "接続", "connection",
        "api エラー", "api error", "rate limit", "503", "502", "500",
    ]

    @classmethod
    def _is_situational(cls, description: str) -> bool:
        """Check if an event describes a situational/transient issue."""
        desc_lower = description.lower()
        return any(kw in desc_lower for kw in cls._SITUATIONAL_KEYWORDS)

    @classmethod
    def _needs_improvement(cls, events: List[dict]) -> Tuple[bool, str]:
        """Determine if a skill needs improvement based on session events.

        - user_correction: excluded from auto-improvement (user-directed fixes
          don't need version increment; resolve only).
        - extra_step: 1+ generalizable event triggers improvement.
          Situational events (timeouts, network errors) are skipped.
        - error_recovery: 1+ triggers improvement.
        - skipped_step: 2+ triggers improvement.
        """
        errors = [e for e in events if e["event_type"] == "error_recovery"]
        extras = [e for e in events if e["event_type"] == "extra_step"]
        skipped = [e for e in events if e["event_type"] == "skipped_step"]

        # Filter extra_steps: keep only generalizable ones
        generalizable_extras = [
            e for e in extras
            if not cls._is_situational(e.get("description", ""))
        ]

        reasons = []
        # user_correction is intentionally excluded — handled by user, no auto-improve
        if errors:
            reasons.append(f"{len(errors)} error_recovery(s)")
        if generalizable_extras:
            reasons.append(
                f"{len(generalizable_extras)} extra_step(s) "
                f"[generalizable]"
            )
        if len(skipped) >= 2:
            reasons.append(f"{len(skipped)} skipped_step(s)")

        return (len(reasons) > 0, ", ".join(reasons))

    # --- Skill Triggers ---

    @classmethod
    def get_all_triggers(cls, user_triggers: list[dict] | None = None) -> list[dict]:
        """Merge default and user-defined skill triggers."""
        triggers = list(cls._DEFAULT_SKILL_TRIGGERS)
        if user_triggers:
            triggers.extend(user_triggers)
        return triggers

    @staticmethod
    def match_triggers(file_path: str, triggers: list[dict]) -> list[str]:
        """Return skill names that match the given file path."""
        from fnmatch import fnmatch

        matched_skills: list[str] = []
        for trigger in triggers:
            if fnmatch(file_path, trigger["pattern"]):
                for skill in trigger["skills"]:
                    if skill not in matched_skills:
                        matched_skills.append(skill)
        return matched_skills

    def check_skill_gaps(
        self, edited_files: list[str], triggers: list[dict]
    ) -> list[dict]:
        """Check which expected skills were not used today."""
        import sqlite3

        expected_skills: dict[str, str] = {}
        for f in edited_files:
            for skill in self.match_triggers(f, triggers):
                if skill not in expected_skills:
                    expected_skills[skill] = f

        if not expected_skills:
            return []

        gaps = []
        with sqlite3.connect(self.db_path) as conn:
            for skill_name, example_file in expected_skills.items():
                row = conn.execute(
                    "SELECT 1 FROM skill_session_events "
                    "WHERE skill_name = ? AND event_type = 'skill_start' "
                    "AND date(timestamp) = date('now', 'localtime')",
                    (skill_name,),
                ).fetchone()
                if row is None:
                    gaps.append(
                        {
                            "file": example_file,
                            "expected_skill": skill_name,
                            "reason": "skill_start not found for today",
                        }
                    )
        return gaps

    def add_session_event(
        self,
        skill_name: str,
        event_type: str,
        description: str,
        step_ref: Optional[str] = None,
    ) -> None:
        """Convenience wrapper: record a skill event with today's date."""
        from datetime import date

        self.track_event(
            session_date=date.today().isoformat(),
            skill_name=skill_name,
            event_type=event_type,
            description=description,
            step_ref=step_ref,
        )

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