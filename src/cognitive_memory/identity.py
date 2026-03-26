"""Identity file read/write operations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Placeholder patterns
_BRACKET_PLACEHOLDER = re.compile(r"^(?:\d+\.\s*)?\[.+\]$")  # [会話から観察された内容] or 1. [...]
_EXAMPLE_ONLY = re.compile(r"^(例:|e\.g\.,)\s*")  # 例: ... / e.g., ...
_EMPTY_FIELD = re.compile(r"^-\s+\S+:\s*$")  # - 名前:  (value empty)
_FIELD_BRACKET = re.compile(r"^-\s+\S+:\s+\[.+\]$")  # - 言語: [日本語 / 英語 / 等]

_HEADING1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_HEADING2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def parse_identity_md(path: Path) -> dict[str, Any]:
    """Parse identity markdown into structured data.

    Returns: {"title": str, "preamble": str, "sections": {heading: content}}
    """
    if not path.exists():
        return {"title": "", "preamble": "", "sections": {}}

    text = path.read_text(encoding="utf-8")

    # Find the first # heading (title)
    title = ""
    preamble = ""
    title_match = _HEADING1.search(text)

    if title_match:
        title = title_match.group(1).strip()
        preamble = text[: title_match.start()].strip()
        body = text[title_match.end() :].lstrip("\n")
    else:
        body = text

    # Split on ## headings
    sections: dict[str, str] = {}
    parts = _HEADING2.split(body)
    # parts[0] is text before first ##, then alternating heading/content
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[heading] = content

    return {"title": title, "preamble": preamble, "sections": sections}


def write_identity_md(path: Path, data: dict[str, Any]) -> None:
    """Write structured data back to identity markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    parts: list[str] = []

    preamble = data.get("preamble", "")
    if preamble:
        parts.append(preamble)
        parts.append("")

    title = data.get("title", "")
    if title:
        parts.append(f"# {title}")
        parts.append("")

    for heading, content in data.get("sections", {}).items():
        parts.append(f"## {heading}")
        parts.append(content)
        parts.append("")

    path.write_text("\n".join(parts) + "\n" if parts else "", encoding="utf-8")


def update_identity_section(path: Path, section: str, content: str) -> None:
    """Update a single section. Creates file if needed."""
    if path.exists():
        data = parse_identity_md(path)
    else:
        # Derive title from filename stem
        stem = path.stem.replace("-", " ").replace("_", " ").title()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"title": stem, "preamble": "", "sections": {}}

    data["sections"][section] = content
    write_identity_md(path, data)


def detect_placeholder_sections(path: Path) -> dict[str, bool]:
    """Detect which sections still have placeholder content.

    Returns: {heading: True if placeholder}. Empty dict if file missing.
    """
    if not path.exists():
        return {}

    data = parse_identity_md(path)
    return {heading: _is_placeholder(content) for heading, content in data["sections"].items()}


def _is_placeholder(content: str) -> bool:
    """Check if section content is placeholder/template text."""
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    # No non-empty lines → placeholder
    if not lines:
        return True

    # Check each line for placeholder indicators
    has_bracket = False
    has_empty_field = False
    all_example = True

    for line in lines:
        if _BRACKET_PLACEHOLDER.match(line):
            has_bracket = True
        if _EMPTY_FIELD.match(line) or _FIELD_BRACKET.match(line):
            has_empty_field = True
        if not _EXAMPLE_ONLY.match(line):
            all_example = False

    # Placeholder if any bracket placeholder or empty field found
    if has_bracket or has_empty_field:
        return True

    # Placeholder if ALL lines are example-only
    if all_example:
        return True

    return False
