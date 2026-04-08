"""cogmem checkpoint — record crystallization checkpoint in cogmem.toml."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from ..config import CogMemConfig


def run_checkpoint() -> None:
    """Update last_checkpoint and checkpoint_count in cogmem.toml."""
    config = CogMemConfig.find_and_load()
    toml_path = Path(config._base_dir) / "cogmem.toml"

    if not toml_path.exists():
        print(f"Error: {toml_path} not found")
        raise SystemExit(1)

    content = toml_path.read_text(encoding="utf-8")
    today = date.today().isoformat()
    new_count = config.checkpoint_count + 1

    crystal_block = (
        f"[cogmem.crystallization]\n"
        f'last_checkpoint = "{today}"\n'
        f"checkpoint_count = {new_count}\n"
    )

    # Preserve any extra keys in the section (e.g. pattern_threshold)
    section_re = re.compile(
        r"^\[cogmem\.crystallization\]\s*\n((?:(?!\[).)*)",
        re.MULTILINE | re.DOTALL,
    )
    match = section_re.search(content)
    if match:
        # Extract non-checkpoint keys from existing section
        extra_lines = []
        for line in match.group(1).splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key = stripped.split("=")[0].strip()
            if key not in ("last_checkpoint", "checkpoint_count"):
                extra_lines.append(line)
        if extra_lines:
            crystal_block += "\n".join(extra_lines) + "\n"
        content = section_re.sub(crystal_block, content)
    else:
        # Append new section
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + crystal_block

    toml_path.write_text(content, encoding="utf-8")
    print(f"Checkpoint recorded: {today} (count: {new_count})")
