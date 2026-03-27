"""Memory decay logic — human-like forgetting mechanism."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class DecayAction(Enum):
    KEEP = "keep"        # 詳細を残す（鮮烈な記憶 or 活発に想起）
    COMPACT = "compact"  # compact に圧縮して詳細削除
    DELETE = "delete"     # 詳細削除（compact 済みなら何もしない）


def evaluate_entry(
    arousal: float,
    recall_count: int,
    last_recalled: str | None,
    arousal_threshold: float = 0.7,
    recall_threshold: int = 2,
    recall_window_months: int = 18,
) -> DecayAction:
    """Evaluate whether a memory entry should be kept, compacted, or deleted.

    Rules (modeled after human memory):
    1. High arousal → always keep (vivid memories persist)
    2. Frequently recalled AND recently recalled → keep (active memories)
    3. Frequently recalled BUT not recalled in window → delete (faded memories)
    4. Everything else → compact (mundane events lose detail, keep gist)
    """
    # Rule 1: Vivid memories persist
    if arousal >= arousal_threshold:
        return DecayAction.KEEP

    # Rule 2 & 3: Recall-based retention
    if recall_count >= recall_threshold:
        if last_recalled is None:
            return DecayAction.DELETE
        last_dt = datetime.fromisoformat(last_recalled)
        window = datetime.now() - timedelta(days=recall_window_months * 30)
        if last_dt >= window:
            return DecayAction.KEEP
        return DecayAction.DELETE

    # Rule 4: Mundane memories → compact
    return DecayAction.COMPACT


def _lookup_recall_data(
    conn: sqlite3.Connection, content_hash: str
) -> tuple[int, Optional[str]]:
    """Look up recall_count and last_recalled from the memories table."""
    row = conn.execute(
        "SELECT recall_count, last_recalled FROM memories WHERE content_hash = ?",
        (content_hash,),
    ).fetchone()
    if row:
        return (row[0] or 0, row[1])
    return (0, None)


def _generate_compact(entries: list, date: str) -> str:
    """Generate compact format from parsed entries.

    Format matches existing .compact.md files:
    - [CATEGORY] title (one line per entry)
    """
    lines = [f"# {date} コンパクトログ"]
    lines.append(f"*decay により圧縮 | 生成: {datetime.now().strftime('%Y-%m-%d')}*")
    lines.append("")
    for entry in entries:
        cat = entry.category or "NOTE"
        # Extract title from content: ### [CATEGORY] title\n...
        title_match = re.match(r"###\s*\[[A-Z]+\]\s*(.+?)(?:\n|$)", entry.content)
        title = title_match.group(1).strip() if title_match else entry.content[:60]
        lines.append(f"- [{cat}] {title}")
    lines.append("")
    return "\n".join(lines)


def apply_decay(config, dry_run: bool = False) -> dict:
    """Apply memory decay to consolidated log files.

    Returns dict with counts: {kept, compacted, deleted, skipped}
    """
    from .parser import parse_entries

    result = {"kept": 0, "compacted": 0, "deleted": 0, "skipped": 0}

    logs_path = config.logs_path
    if not logs_path.exists():
        return result

    # No checkpoint means consolidation hasn't run yet — skip everything
    if not config.last_checkpoint:
        md_files = [
            f for f in sorted(logs_path.glob("*.md"))
            if not f.name.endswith(".compact.md")
        ]
        result["skipped"] = len(md_files)
        return result

    checkpoint_date = config.last_checkpoint

    # Open DB connection for recall data lookup
    db_path = config.database_path
    conn = None
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

    try:
        # List all .md log files (exclude .compact.md)
        md_files = sorted(
            f for f in logs_path.glob("*.md")
            if not f.name.endswith(".compact.md")
        )

        for log_file in md_files:
            # Extract date from filename
            date_match = re.match(r"(\d{4}-\d{2}-\d{2})", log_file.name)
            if not date_match:
                continue
            file_date = date_match.group(1)

            # Only process files BEFORE last_checkpoint
            if file_date >= checkpoint_date:
                result["skipped"] += 1
                continue

            # Parse entries
            md_text = log_file.read_text(encoding="utf-8")
            entries = list(parse_entries(md_text, file_date, config.handover_delimiter))

            if not entries:
                result["skipped"] += 1
                continue

            # Evaluate each entry
            has_keep = False
            for entry in entries:
                content_hash = hashlib.sha256(entry.content.encode()).hexdigest()
                recall_count, last_recalled = (0, None)
                if conn:
                    recall_count, last_recalled = _lookup_recall_data(conn, content_hash)

                action = evaluate_entry(
                    arousal=entry.arousal,
                    recall_count=recall_count,
                    last_recalled=last_recalled,
                    arousal_threshold=config.decay_arousal_threshold,
                    recall_threshold=config.decay_recall_threshold,
                    recall_window_months=config.decay_recall_window_months,
                )

                if action == DecayAction.KEEP:
                    has_keep = True
                    break

            if has_keep:
                result["kept"] += 1
                # Preserve detail file
                continue

            # All entries are COMPACT or DELETE → generate compact + delete detail
            compact_file = logs_path / f"{file_date}.compact.md"

            if not dry_run:
                # Generate compact version (unless it already exists)
                if not compact_file.exists():
                    compact_content = _generate_compact(entries, file_date)
                    compact_file.write_text(compact_content, encoding="utf-8")
                # Delete detail file
                log_file.unlink()
            result["compacted"] += 1

    finally:
        if conn:
            conn.close()

    return result
