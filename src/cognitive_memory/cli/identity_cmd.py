"""cogmem identity — view and update identity files."""
from __future__ import annotations

import json
import sys

from ..config import CogMemConfig
from ..identity import parse_identity_md, update_identity_section, detect_placeholder_sections


def run_identity_update(target, section=None, content=None, json_input=None):
    config = CogMemConfig.find_and_load()
    path = config.identity_user_path if target == "user" else config.identity_soul_path
    if json_input:
        try:
            sections = json.loads(json_input)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)
        for sec, val in sections.items():
            update_identity_section(path, sec, val)
        print(f"Updated {len(sections)} sections in {target}.md")
    elif section and content:
        update_identity_section(path, section, content)
        print(f"Updated [{section}] in {target}.md")
    else:
        print("Error: --section + --content or --json required", file=sys.stderr)
        sys.exit(1)


def run_identity_show(target=None):
    config = CogMemConfig.find_and_load()
    targets = []
    if target in (None, "user"):
        targets.append(("User Profile", config.identity_user_path))
    if target in (None, "soul"):
        targets.append(("Agent Identity", config.identity_soul_path))
    for label, path in targets:
        data = parse_identity_md(path)
        print(f"=== {label} ({path}) ===")
        if not data["sections"]:
            print("  (empty)")
            continue
        for heading, content in data["sections"].items():
            print(f"\n## {heading}")
            print(content)
        print()


def run_identity_detect(target=None, json_output=False):
    config = CogMemConfig.find_and_load()
    targets = []
    if target in (None, "user"):
        targets.append(("user", config.identity_user_path))
    if target in (None, "soul"):
        targets.append(("soul", config.identity_soul_path))
    results = {}
    for name, path in targets:
        results[name] = detect_placeholder_sections(path)
    if json_output:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for name, sections in results.items():
            if not sections:
                print(f"{name}: (no file)")
                continue
            for sec, is_placeholder in sections.items():
                status = "placeholder" if is_placeholder else "filled"
                print(f"{name}/{sec}: {status}")
