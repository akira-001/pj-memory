"""cogmem upgrade-check — check PyPI for newer cogmem-agent and offer to install.

Designed to be invoked from session-init to surface upgrade opportunities to
the user with a single prompt, while staying out of the way otherwise:

- Cached for 24h via [updates].last_check in cogmem.toml (override with --force)
- Hard skip if `[updates].auto = "never"` is set
- `[updates].skip_until = "YYYY-MM-DD"` skips until that date
- JSON output mode for programmatic consumers (session-init)
- Fail-open on any network/parse error so we never block the user
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .. import _version

PYPI_URL = "https://pypi.org/pypi/cogmem-agent/json"
PYPI_TIMEOUT_SEC = 5
CACHE_TTL_HOURS = 24


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if sys.version_info >= (3, 11):
        import tomllib as _toml
    else:
        try:
            import tomli as _toml  # type: ignore[no-redef]
        except ImportError:
            return {}
    try:
        return _toml.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_updates_section(toml_path: Path, updates: dict[str, str]) -> None:
    """Write/merge `[updates]` section. Preserves other sections via plain text edit."""
    existing = toml_path.read_text(encoding="utf-8") if toml_path.exists() else ""
    lines = existing.splitlines()
    out: list[str] = []
    in_updates = False
    seen_updates = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_updates:
                in_updates = False  # leaving updates section
            if stripped == "[updates]":
                in_updates = True
                seen_updates = True
                out.append(line)
                for k, v in updates.items():
                    out.append(f'{k} = "{v}"')
                continue
        if in_updates:
            # Skip existing keys in updates section (we just wrote new ones)
            if "=" in line and stripped and not stripped.startswith("#"):
                continue
        out.append(line)
    if not seen_updates:
        if out and out[-1].strip():
            out.append("")
        out.append("[updates]")
        for k, v in updates.items():
            out.append(f'{k} = "{v}"')
    toml_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _parse_version(s: str) -> tuple[int, ...]:
    """Tiny SemVer-ish parser. Returns tuple for ordered comparison."""
    parts: list[int] = []
    for chunk in s.split(".")[:3]:
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _fetch_latest_pypi() -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(
            PYPI_URL,
            headers={"Accept": "application/json", "User-Agent": "cogmem-agent/upgrade-check"},
        )
        with urllib.request.urlopen(req, timeout=PYPI_TIMEOUT_SEC) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        info = data.get("info", {})
        return {
            "version": info.get("version", ""),
            "summary": info.get("summary", ""),
            "release_date": _extract_release_date(data, info.get("version", "")),
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return None


def _extract_release_date(data: dict[str, Any], version: str) -> str:
    releases = data.get("releases", {})
    files = releases.get(version, [])
    if files:
        upload = files[0].get("upload_time", "")
        if upload:
            return upload.split("T")[0]
    return ""


def _within_cache(last_check_iso: str) -> bool:
    if not last_check_iso:
        return False
    try:
        last = datetime.fromisoformat(last_check_iso)
    except ValueError:
        return False
    return datetime.now() - last < timedelta(hours=CACHE_TTL_HOURS)


def _within_skip(skip_until_iso: str) -> bool:
    if not skip_until_iso:
        return False
    try:
        skip = date.fromisoformat(skip_until_iso)
    except ValueError:
        return False
    return date.today() <= skip


def run_upgrade_check(
    *,
    base_dir: Path | None = None,
    json_output: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Check PyPI for a newer cogmem-agent. Returns a result dict.

    Result schema (also emitted as JSON when json_output=True):
        {
          "status": "up_to_date" | "upgrade_available" | "skipped" | "error",
          "current": "0.24.0",
          "latest": "0.25.0" | None,
          "release_date": "2026-04-26" | "",
          "summary": "...",
          "reason": "skip_until=..." | "auto=never" | "cached" | None,
          "upgrade_command": "pip install -U cogmem-agent" | None,
          "post_install": "cogmem init" | None,
        }
    """
    base = base_dir or Path.cwd()
    toml_path = base / "cogmem.toml"
    cfg = _read_toml(toml_path)
    updates_section = cfg.get("updates", {}) if isinstance(cfg.get("updates"), dict) else {}

    current = _version.__version__
    # Skill-template drift: independent of PyPI check, helps existing users pick up
    # template improvements that `cogmem init` skip-protects. Scoped to the user's
    # preferred language (read from cogmem.toml [cogmem].lang).
    skill_template_updates = _count_skill_template_drift(base)

    result: dict[str, Any] = {
        "status": "up_to_date",
        "current": current,
        "latest": None,
        "release_date": "",
        "summary": "",
        "reason": None,
        "upgrade_command": None,
        "post_install": None,
        "skill_template_updates": skill_template_updates,
    }

    auto = str(updates_section.get("auto", "ask")).lower()
    if auto == "never" and not force:
        result["status"] = "skipped"
        result["reason"] = "auto=never"
        _emit(result, json_output)
        return result

    skip_until = str(updates_section.get("skip_until", ""))
    if skip_until and _within_skip(skip_until) and not force:
        result["status"] = "skipped"
        result["reason"] = f"skip_until={skip_until}"
        _emit(result, json_output)
        return result

    last_check = str(updates_section.get("last_check", ""))
    if last_check and _within_cache(last_check) and not force:
        result["status"] = "skipped"
        result["reason"] = "cached"
        _emit(result, json_output)
        return result

    pypi = _fetch_latest_pypi()
    if pypi is None:
        result["status"] = "error"
        result["reason"] = "pypi_unreachable"
        _emit(result, json_output)
        return result

    latest = pypi["version"]
    result["latest"] = latest
    result["release_date"] = pypi["release_date"]
    result["summary"] = pypi["summary"]

    if _parse_version(latest) > _parse_version(current):
        result["status"] = "upgrade_available"
        result["upgrade_command"] = "pip install -U cogmem-agent"
        result["post_install"] = "cogmem init"
    else:
        result["status"] = "up_to_date"

    if toml_path.exists():
        _write_updates_section(toml_path, {"last_check": datetime.now().isoformat(timespec="seconds")})

    _emit(result, json_output)
    return result


def mark_skip_until(base_dir: Path, days: int = 7) -> None:
    """Helper for callers: postpone the next prompt by N days."""
    skip_date = (date.today() + timedelta(days=days)).isoformat()
    toml_path = base_dir / "cogmem.toml"
    if toml_path.exists():
        _write_updates_section(toml_path, {
            "skip_until": skip_date,
            "last_check": datetime.now().isoformat(timespec="seconds"),
        })


def get_user_lang(base_dir: Path | None = None) -> str:
    """Read user's preferred language from `cogmem.toml [cogmem].lang`.

    Falls back to 'en' if the file or key is missing. Used to scope drift detection
    and other locale-aware operations to the user's actual installed templates.
    """
    base = base_dir or Path.cwd()
    cfg = _read_toml(base / "cogmem.toml")
    section = cfg.get("cogmem", {}) if isinstance(cfg.get("cogmem"), dict) else {}
    lang = str(section.get("lang", "en")).lower()
    return lang if lang in ("en", "ja") else "en"


def set_cogmem_lang(toml_path: Path, lang: str) -> None:
    """Set or update `[cogmem].lang` in cogmem.toml. Idempotent.

    Preserves all other sections / keys; rewrites only the lang line under [cogmem].
    """
    if lang not in ("en", "ja"):
        return
    if not toml_path.exists():
        return
    text = toml_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    in_cogmem = False
    wrote_lang = False
    for line in lines:
        stripped = line.strip()
        is_section_header = stripped.startswith("[") and stripped.endswith("]")
        if is_section_header:
            if in_cogmem and not wrote_lang:
                out.append(f'lang = "{lang}"')
                wrote_lang = True
            in_cogmem = (stripped == "[cogmem]")
        if in_cogmem and re.match(r'^\s*lang\s*=', line):
            out.append(f'lang = "{lang}"')
            wrote_lang = True
            continue
        out.append(line)
    if in_cogmem and not wrote_lang:
        out.append(f'lang = "{lang}"')
        wrote_lang = True
    if not wrote_lang:
        # [cogmem] section not found — leave the file unchanged. Fabricating a
        # section would surprise users who own the existing toml and could
        # collide with malformed configs. Lang persistence requires a valid
        # [cogmem] section (always present in templates from `cogmem init`).
        return
    toml_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _count_skill_template_drift(base_dir: Path | None = None) -> int:
    """Count installed skills whose SKILL.md differs from the packaged template
    in the user's preferred language. Returns 0 on any error (fail-open).
    """
    try:
        from .skills_update_cmd import detect_diffs
        lang = get_user_lang(base_dir)
        return len(detect_diffs(lang=lang))
    except Exception:
        return 0


def _emit(result: dict[str, Any], json_output: bool) -> None:
    if json_output:
        print(json.dumps(result, ensure_ascii=False))
        return
    status = result["status"]
    if status == "upgrade_available":
        print(f"📦 cogmem-agent {result['latest']} is available (current: {result['current']})")
        if result["release_date"]:
            print(f"   Released: {result['release_date']}")
        if result["summary"]:
            print(f"   {result['summary']}")
        print()
        print("To upgrade:")
        print(f"  {result['upgrade_command']}")
        print(f"  {result['post_install']}    # picks up new bundled skills")
    elif status == "up_to_date":
        print(f"✓ cogmem-agent is up to date ({result['current']})")
    elif status == "skipped":
        print(f"  upgrade-check skipped (reason={result['reason']})")
    elif status == "error":
        print(f"  upgrade-check failed (reason={result['reason']})", file=sys.stderr)
    drift = result.get("skill_template_updates", 0)
    if drift > 0:
        print(f"📝 {drift} installed skill(s) have template updates available")
        print(f"   Run: cogmem skills update-templates  (use --dry-run first)")
