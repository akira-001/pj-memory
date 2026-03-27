"""Personality service for dashboard."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, List

from ...config import CogMemConfig
from ...identity import parse_identity_md, update_identity_section


def get_personality_data(config: CogMemConfig) -> dict[str, Any]:
    """Read identity files and learning timeline."""
    soul_data = parse_identity_md(config.identity_soul_path)
    user_data = parse_identity_md(config.identity_user_path)
    learning = _get_learning_timeline(config)
    knowledge = _read_file_or_empty(config.knowledge_summary_path)
    return {
        "soul": soul_data["sections"],
        "user": user_data["sections"],
        "learning": learning,
        "knowledge": knowledge,
    }


def update_section(config: CogMemConfig, target: str, section: str, content: str) -> None:
    """Update a section in user or soul identity file."""
    if target == "user":
        path = config.identity_user_path
    elif target == "soul":
        path = config.identity_soul_path
    else:
        raise ValueError(f"Invalid target: {target}. Must be 'user' or 'soul'.")
    update_identity_section(path, section, content)


def _read_file_or_empty(path: Path) -> str:
    """Read file content or return empty string."""
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _get_learning_timeline(config: CogMemConfig) -> List[dict[str, Any]]:
    """Get INSIGHT entries from memories DB as learning timeline."""
    db_path = config.database_path
    if not Path(db_path).exists():
        return []

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT date, content, arousal FROM memories "
            "WHERE content LIKE '%[INSIGHT]%' "
            "ORDER BY date DESC, id DESC LIMIT 50"
        ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            # Extract title from content (### [INSIGHT] Title)
            title_match = re.search(r"\[INSIGHT\]\s*(.*?)(?:\n|$)", row["content"])
            title = title_match.group(1).strip() if title_match else "Insight"
            # Get first content line (after header and metadata)
            lines = row["content"].split("\n")
            body_lines = [
                l
                for l in lines[1:]
                if l.strip() and not l.strip().startswith("*Arousal")
            ]
            body = body_lines[0].strip() if body_lines else ""

            results.append(
                {
                    "date": row["date"],
                    "title": title,
                    "body": body[:200],
                    "arousal": row["arousal"],
                }
            )

        return results
    except sqlite3.Error:
        return []
    finally:
        if conn is not None:
            conn.close()
