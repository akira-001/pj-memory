"""Log file service for dashboard log browser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional

from ...config import CogMemConfig
from ...parser import parse_entries
from ...types import MemoryEntry

# Valid category tags used in log entries
_VALID_CATEGORIES = {"INSIGHT", "DECISION", "ERROR", "PATTERN", "QUESTION", "MILESTONE", "SKILL", "SUMMARY"}


def _collect_dates(logs_path: Path) -> dict[str, dict[str, bool]]:
    """Collect all unique dates from logs_path with existence flags for .md and .compact.md."""
    dates: dict[str, dict[str, bool]] = {}
    for f in logs_path.glob("*.md"):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if not m:
            continue
        date = m.group(1)
        if date not in dates:
            dates[date] = {"has_md": False, "has_compact": False}
        if f.name.endswith(".compact.md"):
            dates[date]["has_compact"] = True
        else:
            dates[date]["has_md"] = True
    return dates


def _determine_status(has_md: bool, has_compact: bool) -> str:
    """Determine lifecycle status from file existence."""
    if has_md and has_compact:
        return "retained"
    if has_compact:
        return "compacted"
    return "detailed"


def _parse_categories_from_compact(text: str) -> dict[str, int]:
    """Extract category counts from compact file format (- [CATEGORY] title lines and ### [CATEGORY])."""
    counts: dict[str, int] = {}
    for line in text.split("\n"):
        line = line.strip()
        # Compact format: - [CATEGORY] title
        m = re.match(r"^- \[([A-Z]+)\]\s+", line)
        if not m:
            # Also check ### [CATEGORY] headings in compact files
            m = re.match(r"^### \[([A-Z]+)\]", line)
        if m:
            cat = m.group(1)
            if cat in _VALID_CATEGORIES:
                counts[cat] = counts.get(cat, 0) + 1
    return counts


def _parse_categories_and_arousal(text: str, date: str, handover_delimiter: str) -> tuple[dict[str, int], Optional[float]]:
    """Parse categories and max arousal from a full log file using parse_entries."""
    counts: dict[str, int] = {}
    max_arousal: Optional[float] = None
    for entry in parse_entries(text, date, handover_delimiter):
        if entry.category and entry.category in _VALID_CATEGORIES:
            counts[entry.category] = counts.get(entry.category, 0) + 1
        if entry.arousal is not None:
            if max_arousal is None or entry.arousal > max_arousal:
                max_arousal = entry.arousal
    return counts, max_arousal


def get_log_dates(config: CogMemConfig) -> List[dict[str, Any]]:
    """List all log files as [{date, has_compact, entry_count, overview, status, categories, max_arousal}, ...] sorted date DESC.

    Scans config.logs_path for *.md files.
    """
    logs_path = config.logs_path
    if not logs_path.exists():
        return []

    date_files = _collect_dates(logs_path)

    results: list[dict[str, Any]] = []
    for date in sorted(date_files.keys(), reverse=True):
        info = date_files[date]
        status = _determine_status(info["has_md"], info["has_compact"])

        text = ""
        entry_count = 0
        overview = ""
        categories: dict[str, int] = {}
        max_arousal: Optional[float] = None

        # Parse from full .md if available
        if info["has_md"]:
            md_path = logs_path / f"{date}.md"
            try:
                text = md_path.read_text(encoding="utf-8")
                entry_count = len(re.findall(r"^### ", text, re.MULTILINE))
            except OSError:
                text = ""

            # Extract overview
            overview_match = re.search(r"## セッション概要\s*\n(.*?)(?=\n## |\n---|\Z)", text, re.DOTALL)
            if overview_match:
                overview = overview_match.group(1).strip()

            categories, max_arousal = _parse_categories_and_arousal(
                text, date, config.handover_delimiter
            )
        elif info["has_compact"]:
            # Parse from compact file only
            compact_path = logs_path / f"{date}.compact.md"
            try:
                compact_text = compact_path.read_text(encoding="utf-8")
                entry_count = len(re.findall(r"^### ", compact_text, re.MULTILINE))
                entry_count += len(re.findall(r"^- \[[A-Z]+\]", compact_text, re.MULTILINE))
            except OSError:
                compact_text = ""

            # Extract overview from compact (## エッセンス section)
            ess_match = re.search(r"## エッセンス\s*\n(.*?)(?=\n## |\n---|\Z)", compact_text, re.DOTALL)
            if ess_match:
                overview = ess_match.group(1).strip()
            else:
                overview_match = re.search(r"## セッション概要\s*\n(.*?)(?=\n## |\n---|\Z)", compact_text, re.DOTALL)
                if overview_match:
                    overview = overview_match.group(1).strip()

            categories = _parse_categories_from_compact(compact_text)
            max_arousal = None  # No arousal data in compact files

        results.append(
            {
                "date": date,
                "has_compact": info["has_compact"],
                "entry_count": entry_count,
                "overview": overview,
                "status": status,
                "categories": categories,
                "max_arousal": max_arousal,
            }
        )

    return results


def get_log_summary(config: CogMemConfig) -> dict[str, Any]:
    """Compute aggregate summary across all log dates.

    Returns {total, detailed, compacted, retained, category_counts}.
    """
    logs_path = config.logs_path
    if not logs_path.exists():
        return {
            "total": 0,
            "detailed": 0,
            "compacted": 0,
            "retained": 0,
            "category_counts": {},
        }

    date_files = _collect_dates(logs_path)
    detailed = 0
    compacted = 0
    retained = 0
    category_counts: dict[str, int] = {}

    for date, info in date_files.items():
        status = _determine_status(info["has_md"], info["has_compact"])
        if status == "detailed":
            detailed += 1
        elif status == "compacted":
            compacted += 1
        else:
            retained += 1

        # Aggregate categories from best available source
        cats: dict[str, int] = {}
        if info["has_md"]:
            md_path = logs_path / f"{date}.md"
            try:
                text = md_path.read_text(encoding="utf-8")
                cats, _ = _parse_categories_and_arousal(
                    text, date, config.handover_delimiter
                )
            except OSError:
                pass
        elif info["has_compact"]:
            compact_path = logs_path / f"{date}.compact.md"
            try:
                compact_text = compact_path.read_text(encoding="utf-8")
                cats = _parse_categories_from_compact(compact_text)
            except OSError:
                pass

        for cat, count in cats.items():
            category_counts[cat] = category_counts.get(cat, 0) + count

    return {
        "total": len(date_files),
        "detailed": detailed,
        "compacted": compacted,
        "retained": retained,
        "category_counts": category_counts,
    }


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
