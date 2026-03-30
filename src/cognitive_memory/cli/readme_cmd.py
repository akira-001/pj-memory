"""cogmem readme — display the package README."""

from __future__ import annotations

import sys


def run_readme(lang: str = "en") -> None:
    """Print the README content from package metadata."""
    try:
        if sys.version_info >= (3, 10):
            from importlib.metadata import metadata
        else:
            from importlib.metadata import metadata
        meta = metadata("cogmem-agent")
    except Exception:
        print("Error: could not read package metadata for cogmem-agent", file=sys.stderr)
        sys.exit(1)

    description = meta.get_payload()
    if not description or not description.strip():
        print("No README found in package metadata.", file=sys.stderr)
        sys.exit(1)

    if lang == "ja":
        # Check if Japanese section exists (marked by the language link)
        # The METADATA only contains the English README; point users to the repo
        repo_url = meta.get("Project-URL", "")
        # Extract repository URL
        urls = meta.get_all("Project-URL") or []
        repo = ""
        for url_entry in urls:
            if "Repository" in url_entry:
                repo = url_entry.split(",", 1)[-1].strip()
                break
        if repo:
            print(f"日本語版READMEはリポジトリで確認できます:\n  {repo}/blob/main/README_ja.md")
        else:
            print("日本語版READMEはリポジトリで確認してください。", file=sys.stderr)
        return

    print(description.strip())
