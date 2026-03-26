"""Memory consolidation data service for the dashboard."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ...config import CogMemConfig
from ...signals import check_signals


def parse_error_patterns(path: Path) -> list[dict[str, str]]:
    """Parse EP-NNN entries from error-patterns.md.

    Returns list of {"id": "EP-001", "title": "...", "date": "..."}.
    """
    if not path.is_file():
        return []

    text = path.read_text(encoding="utf-8")
    patterns: list[dict[str, str]] = []

    for match in re.finditer(
        r"^## (EP-\d+):\s*(.+?)$\n\*\*発生\*\*:\s*(\S+)",
        text,
        re.MULTILINE,
    ):
        patterns.append({
            "id": match.group(1),
            "title": match.group(2).strip(),
            "date": match.group(3),
        })

    return patterns


def _md_to_html(text: str) -> str:
    """Convert minimal markdown to HTML (bold, inline code, list items)."""
    import html as html_mod

    lines = text.strip().split("\n")
    result: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        escaped = html_mod.escape(line)
        # Bold: **text**
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        # Inline code: `text`
        escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
        # List items: - text
        if escaped.startswith("- "):
            escaped = escaped[2:]
            result.append(f"<li>{escaped}</li>")
        # Numbered list: 1. text
        elif re.match(r"^\d+\.\s", escaped):
            escaped = re.sub(r"^\d+\.\s", "", escaped)
            result.append(f"<li>{escaped}</li>")
        else:
            result.append(f"<p>{escaped}</p>")

    # Wrap consecutive <li> elements in <ul>
    output: list[str] = []
    in_list = False
    for item in result:
        if item.startswith("<li>"):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(item)
        else:
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(item)
    if in_list:
        output.append("</ul>")

    return "\n".join(output)


def parse_principles(path: Path) -> list[dict[str, str]]:
    """Parse principles from knowledge summary.

    Looks for ### headings under '## 確立された判断原則'.
    Returns list of {"title": "...", "body": "...", "body_html": "..."}.
    """
    if not path.is_file():
        return []

    text = path.read_text(encoding="utf-8")

    # Find the principles section
    section_match = re.search(
        r"^## 確立された判断原則\s*\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not section_match:
        return []

    section = section_match.group(1)
    principles: list[dict[str, str]] = []

    # Split by ### headings
    for match in re.finditer(
        r"^### \d+\.\s*(.+?)$\n(.*?)(?=^### |\Z)",
        section,
        re.MULTILINE | re.DOTALL,
    ):
        body = match.group(2).strip()
        principles.append({
            "title": match.group(1).strip(),
            "body": body,
            "body_html": _md_to_html(body),
        })

    return principles


def get_crystallization_data(config: CogMemConfig) -> dict[str, Any]:
    """Get all crystallization data for the dashboard page."""
    signals = check_signals(config)
    error_patterns = parse_error_patterns(config.knowledge_error_patterns_path)
    principles = parse_principles(config.knowledge_summary_path)

    return {
        "signals": signals,
        "error_patterns": error_patterns,
        "principles": principles,
        "checkpoint": {
            "last": config.last_checkpoint,
            "count": config.checkpoint_count,
        },
    }
