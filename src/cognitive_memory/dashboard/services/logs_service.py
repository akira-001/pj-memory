"""Log file service for dashboard log browser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional

from ...config import CogMemConfig
from ...parser import parse_entries
from ...types import MemoryEntry


def get_log_dates(config: CogMemConfig) -> List[dict[str, Any]]:
    """List all log files as [{date, has_compact, entry_count_approx}, ...] sorted date DESC.

    Scans config.logs_path for *.md files (excluding .compact.md).
    """
    logs_path = config.logs_path
    if not logs_path.exists():
        return []

    results: list[dict[str, Any]] = []
    for f in sorted(logs_path.glob("*.md"), reverse=True):
        if f.name.endswith(".compact.md"):
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.stem)
        if not m:
            continue
        date = m.group(1)
        compact_path = logs_path / f"{date}.compact.md"
        # Approximate entry count by counting ### headings
        try:
            text = f.read_text(encoding="utf-8")
            entry_count = len(re.findall(r"^### ", text, re.MULTILINE))
        except OSError:
            text = ""
            entry_count = 0

        # Extract session overview
        overview = ""
        overview_match = re.search(r"## セッション概要\s*\n(.*?)(?=\n## |\n---|\Z)", text, re.DOTALL)
        if overview_match:
            overview = overview_match.group(1).strip()

        results.append(
            {
                "date": date,
                "has_compact": compact_path.exists(),
                "entry_count": entry_count,
                "overview": overview,
            }
        )

    return results


def get_log_entries(
    config: CogMemConfig,
    date: str,
    category: Optional[str] = None,
    sort: str = "time",
    query: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Read a log file and return parsed entries with metadata.

    Returns None if the log file does not exist.
    Returns {
        date: str,
        overview: str,
        handover: str,
        entries: [dict, ...],
    }
    """
    logs_path = config.logs_path
    log_file = (logs_path / f"{date}.md").resolve()
    if not str(log_file).startswith(str(logs_path.resolve())):
        return None
    if not log_file.exists():
        return None

    try:
        md_text = log_file.read_text(encoding="utf-8")
    except OSError:
        return None

    # Extract overview section
    overview = ""
    overview_match = re.search(
        r"## セッション概要\s*\n(.*?)(?=\n## |\n---|\Z)",
        md_text,
        re.DOTALL,
    )
    if overview_match:
        overview = overview_match.group(1).strip()

    # Extract handover section
    handover = ""
    handover_match = re.search(
        r"## 引き継ぎ\s*\n(.*?)(?=\n## |\Z)",
        md_text,
        re.DOTALL,
    )
    if handover_match:
        handover = handover_match.group(1).strip()

    # Parse entries
    raw_entries = list(parse_entries(md_text, date, config.handover_delimiter))

    # Convert to dicts with extracted title, emotion, body
    entries: list[dict[str, Any]] = []
    for entry in raw_entries:
        parsed = _parse_entry_content(entry)
        entries.append(parsed)

    # Apply category filter
    if category:
        entries = [e for e in entries if e["category"] == category]

    # Apply text search filter
    if query:
        q_lower = query.lower()
        entries = [
            e
            for e in entries
            if q_lower in e["title"].lower()
            or q_lower in e["body"].lower()
            or q_lower in (e["category"] or "").lower()
        ]

    # Apply sort
    if sort == "arousal":
        entries.sort(key=lambda e: e["arousal"], reverse=True)

    return {
        "date": date,
        "overview": overview,
        "handover": handover,
        "entries": entries,
    }


def _parse_entry_content(entry: MemoryEntry) -> dict[str, Any]:
    """Extract title, emotion, and body from a MemoryEntry's content."""
    lines = entry.content.split("\n")

    # Title from first line (### [CATEGORY] Title)
    title = ""
    if lines:
        first_line = lines[0].lstrip("#").strip()
        # Remove category tags like [INSIGHT]
        title = re.sub(r"\[([A-Z]+)\]\s*", "", first_line).strip()

    # Extract emotion from metadata line
    emotion = ""
    body_lines: list[str] = []
    for line in lines[1:]:
        emotion_match = re.search(r"Emotion:\s*(.+?)(?:\s*\*|\s*\||\s*$)", line)
        if emotion_match and not emotion:
            emotion = emotion_match.group(1).strip()
            continue
        # Skip the arousal metadata line
        if re.match(r"^\s*\*?Arousal:", line):
            continue
        body_lines.append(line)

    body = "\n".join(body_lines).strip()

    return {
        "title": title,
        "category": entry.category,
        "arousal": entry.arousal,
        "emotion": emotion,
        "body": body,
        "date": entry.date,
    }
