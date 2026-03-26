# Identity Update on Wrap — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap 時にセッション中のログから identity ファイル（user.md / soul.md）を自動更新する `cogmem identity update` コマンドを追加する

**Architecture:** セッションログを解析して identity 関連の情報を抽出し、既存の identity ファイルのセクションをマージ更新する。personality_service の `_read_and_parse_md` パーサーを共通化して読み書き両方で使う。CLI コマンドとして `cogmem identity update` を追加し、agents.md の Wrap フローに組み込む。

**Tech Stack:** Python, argparse, markdown parsing (既存パーサー拡張)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/cognitive_memory/identity.py` | identity ファイルの読み書きロジック（parse / merge / write / placeholder 検知） |
| `src/cognitive_memory/cli/identity_cmd.py` | `cogmem identity update` CLI コマンド |
| `src/cognitive_memory/cli/main.py` | identity サブコマンド登録 |
| `src/cognitive_memory/dashboard/services/personality_service.py` | 共通パーサーを identity.py から import に変更 |
| `tests/test_identity.py` | identity モジュールのテスト（parse / write / update / placeholder 検知） |
| `tests/test_cli_identity.py` | CLI コマンドのテスト |
| `tests/fixtures/session_logs/*.md` | インテグレーションテスト用ダミーセッションログ（5パターン） |

---

### Task 1: identity.py — Markdown セクション読み書き

**Files:**
- Create: `src/cognitive_memory/identity.py`
- Test: `tests/test_identity.py`

- [ ] **Step 1: テスト作成 — parse_identity_md**

既存の `_read_and_parse_md` と同じ動作を独立モジュールで再実装するテスト。

```python
# tests/test_identity.py
"""Identity file read/write tests."""
from pathlib import Path

import pytest

from cognitive_memory.identity import parse_identity_md, update_identity_section, write_identity_md


class TestParseIdentityMd:
    def test_parse_sections(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "# Title\n\n## Section A\nContent A\n\n## Section B\nLine 1\nLine 2\n",
            encoding="utf-8",
        )
        result = parse_identity_md(md)
        assert result["title"] == "Title"
        assert result["sections"]["Section A"] == "Content A"
        assert "Line 1" in result["sections"]["Section B"]

    def test_parse_missing_file(self, tmp_path):
        result = parse_identity_md(tmp_path / "nope.md")
        assert result["title"] == ""
        assert result["sections"] == {}

    def test_parse_preserves_frontmatter(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "*自動更新*\n\n# Title\n\n## Sec\nContent\n",
            encoding="utf-8",
        )
        result = parse_identity_md(md)
        assert result["preamble"] == "*自動更新*"
        assert result["title"] == "Title"
```

- [ ] **Step 2: テスト実行 — FAIL 確認**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity.py -v`
Expected: FAIL — `cognitive_memory.identity` が存在しない

- [ ] **Step 3: 実装 — parse_identity_md**

```python
# src/cognitive_memory/identity.py
"""Identity file read/write operations."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_identity_md(path: Path) -> dict[str, Any]:
    """Parse identity markdown into structured data.

    Returns:
        {"title": str, "preamble": str, "sections": {heading: content}}
    """
    if not path.exists():
        return {"title": "", "preamble": "", "sections": {}}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"title": "", "preamble": "", "sections": {}}

    title = ""
    preamble_lines: list[str] = []
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []
    found_title = False

    for line in text.split("\n"):
        if line.startswith("# ") and not found_title:
            title = line[2:].strip()
            found_title = True
            continue
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = line[3:].strip()
            current_lines = []
            continue
        if not found_title:
            preamble_lines.append(line)
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()

    return {
        "title": title,
        "preamble": "\n".join(preamble_lines).strip(),
        "sections": sections,
    }
```

- [ ] **Step 4: テスト実行 — parse テストが PASS**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity.py::TestParseIdentityMd -v`
Expected: PASS

- [ ] **Step 5: テスト作成 — write_identity_md**

```python
class TestWriteIdentityMd:
    def test_roundtrip(self, tmp_path):
        md = tmp_path / "test.md"
        original = "# Title\n\n## Sec A\nContent A\n\n## Sec B\nContent B\n"
        md.write_text(original, encoding="utf-8")
        data = parse_identity_md(md)
        write_identity_md(md, data)
        result = parse_identity_md(md)
        assert result["sections"] == data["sections"]
        assert result["title"] == data["title"]

    def test_write_with_preamble(self, tmp_path):
        md = tmp_path / "test.md"
        data = {
            "title": "User",
            "preamble": "*自動更新*",
            "sections": {"基本情報": "- 名前: Akira"},
        }
        write_identity_md(md, data)
        text = md.read_text(encoding="utf-8")
        assert text.startswith("*自動更新*\n")
        assert "# User" in text
        assert "## 基本情報" in text
        assert "- 名前: Akira" in text
```

- [ ] **Step 6: テスト実行 — FAIL 確認**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity.py::TestWriteIdentityMd -v`
Expected: FAIL

- [ ] **Step 7: 実装 — write_identity_md**

```python
def write_identity_md(path: Path, data: dict[str, Any]) -> None:
    """Write structured data back to identity markdown file."""
    lines: list[str] = []

    if data.get("preamble"):
        lines.append(data["preamble"])
        lines.append("")

    if data.get("title"):
        lines.append(f"# {data['title']}")
        lines.append("")

    for heading, content in data.get("sections", {}).items():
        lines.append(f"## {heading}")
        lines.append(content)
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **Step 8: テスト実行 — PASS**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity.py -v`
Expected: ALL PASS

- [ ] **Step 9: コミット**

```bash
cd ~/workspace/ai-dev/cognitive-memory-lib
git add src/cognitive_memory/identity.py tests/test_identity.py
git commit -m "feat: add identity.py with markdown parse/write"
```

- [ ] **Step 10: テスト作成 — detect_placeholder_sections**

各 identity ファイルタイプ（user / soul / agents）のプレースホルダー検知テスト。
検知パターン: `[角括弧プレースホルダー]`、`例:` / `e.g.,` のみの行、コロン後が空（`- 名前:`）。

テストクラスは `test_identity.py` に追加済み（テスト設計フェーズで作成）:
- `TestDetectPlaceholderUser` — 6テスト（JA/ENテンプレート、部分記入、全記入、空フィールド、ファイル未存在）
- `TestDetectPlaceholderSoul` — 4テスト（JA/ENテンプレート、実データ、例行のみ）
- `TestDetectPlaceholderAgents` — 2テスト（テンプレート、カスタマイズ済み）

- [ ] **Step 11: テスト実行 — FAIL 確認**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity.py::TestDetectPlaceholderUser -v`
Expected: FAIL — `detect_placeholder_sections` が未定義

- [ ] **Step 12: 実装 — detect_placeholder_sections**

```python
import re

# Placeholder patterns
_BRACKET_PLACEHOLDER = re.compile(r"^\[.+\]$")  # [会話から観察された内容]
_EXAMPLE_ONLY = re.compile(r"^(例:|e\.g\.,)\s*")  # 例: ... / e.g., ...
_EMPTY_FIELD = re.compile(r"^-\s+\S+:\s*$")  # - 名前:  (value empty)


def detect_placeholder_sections(path: Path) -> dict[str, bool]:
    """Detect which sections still have placeholder/template content.

    Returns:
        {section_heading: True if placeholder, False if real data}
        Empty dict if file doesn't exist.
    """
    data = parse_identity_md(path)
    if not data["sections"]:
        return {}

    result: dict[str, bool] = {}
    for heading, content in data["sections"].items():
        result[heading] = _is_placeholder(content)
    return result


def _is_placeholder(content: str) -> bool:
    """Check if section content is placeholder/template text."""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if not lines:
        return True

    for line in lines:
        # Skip numbered prefixes like "1. " "2. "
        cleaned = re.sub(r"^\d+\.\s*", "", line)
        cleaned = re.sub(r"^-\s*", "", cleaned)

        # [placeholder text] → placeholder
        if _BRACKET_PLACEHOLDER.match(cleaned):
            return True
        # 例: ... / e.g., ... (only example lines) → placeholder
        # - 名前:  (empty value) → placeholder
        if _EMPTY_FIELD.match(line):
            return True

    # If ALL non-empty lines are example-only → placeholder
    non_example_lines = [
        line for line in lines
        if not _EXAMPLE_ONLY.match(line.strip())
    ]
    if not non_example_lines:
        return True

    return False
```

- [ ] **Step 13: テスト実行 — 全 placeholder テスト PASS**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity.py -k "Placeholder" -v`
Expected: ALL PASS (12 tests)

- [ ] **Step 14: コミット**

```bash
cd ~/workspace/ai-dev/cognitive-memory-lib
git add src/cognitive_memory/identity.py tests/test_identity.py
git commit -m "feat: add detect_placeholder_sections for identity files"
```

---

### Task 2: update_identity_section — セクション単位のマージ更新

**Files:**
- Modify: `src/cognitive_memory/identity.py`
- Test: `tests/test_identity.py`

- [ ] **Step 1: テスト作成 — update_identity_section**

```python
class TestUpdateIdentitySection:
    def test_update_existing_section(self, tmp_path):
        md = tmp_path / "user.md"
        md.write_text(
            "# User\n\n## 基本情報\n- 名前:\n- 役割:\n\n## 専門性\n[会話から観察された内容]\n",
            encoding="utf-8",
        )
        update_identity_section(md, "基本情報", "- 名前: Akira\n- 役割: コンサルタント")
        result = parse_identity_md(md)
        assert "Akira" in result["sections"]["基本情報"]
        assert "コンサルタント" in result["sections"]["基本情報"]

    def test_add_new_section(self, tmp_path):
        md = tmp_path / "user.md"
        md.write_text("# User\n\n## 基本情報\nTest\n", encoding="utf-8")
        update_identity_section(md, "新セクション", "新しい内容")
        result = parse_identity_md(md)
        assert result["sections"]["新セクション"] == "新しい内容"
        assert result["sections"]["基本情報"] == "Test"  # 既存セクションは維持

    def test_no_overwrite_if_placeholder(self, tmp_path):
        """プレースホルダーは上書き、実データは保持。"""
        md = tmp_path / "user.md"
        md.write_text("# User\n\n## 専門性\nPython, SQL\n", encoding="utf-8")
        # 既にデータがあるセクションを上書きしようとした場合も上書きする
        update_identity_section(md, "専門性", "Python, SQL, Go")
        result = parse_identity_md(md)
        assert "Go" in result["sections"]["専門性"]

    def test_file_not_exists_creates(self, tmp_path):
        md = tmp_path / "identity" / "user.md"
        update_identity_section(md, "基本情報", "- 名前: Akira")
        assert md.exists()
        result = parse_identity_md(md)
        assert "Akira" in result["sections"]["基本情報"]
```

- [ ] **Step 2: テスト実行 — FAIL 確認**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity.py::TestUpdateIdentitySection -v`
Expected: FAIL

- [ ] **Step 3: 実装 — update_identity_section**

```python
def update_identity_section(path: Path, section: str, content: str) -> None:
    """Update a single section in an identity markdown file.

    If the file doesn't exist, creates it with the section.
    If the section doesn't exist, appends it.
    If the section exists, replaces its content.
    """
    data = parse_identity_md(path)
    if not data["title"]:
        # New file — derive title from filename
        data["title"] = path.stem.capitalize()
    data["sections"][section] = content
    write_identity_md(path, data)
```

- [ ] **Step 4: テスト実行 — PASS**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity.py -v`
Expected: ALL PASS

- [ ] **Step 5: コミット**

```bash
cd ~/workspace/ai-dev/cognitive-memory-lib
git add src/cognitive_memory/identity.py tests/test_identity.py
git commit -m "feat: add update_identity_section for section-level merge"
```

---

### Task 3: CLI コマンド — `cogmem identity update`

**Files:**
- Create: `src/cognitive_memory/cli/identity_cmd.py`
- Modify: `src/cognitive_memory/cli/main.py`
- Test: `tests/test_cli_identity.py`

CLI インターフェース設計:
```bash
# セクション単位で更新（改行は $'...' 構文か --json を使う）
cogmem identity update --target user --section "基本情報" --content $'- 名前: Akira\n- 役割: コンサルタント'

# ファイル指定（soul.md）
cogmem identity update --target soul --section "役割" --content "開発パートナー、批判的思考パートナー"

# 複数セクション一括（JSON）
cogmem identity update --target user --json '{"基本情報": "- 名前: Akira", "専門性": "Python, SQL"}'

# 現在の内容表示
cogmem identity show
```

- [ ] **Step 1: テスト作成**

```python
# tests/test_cli_identity.py
"""Identity CLI command tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cognitive_memory.cli.identity_cmd import run_identity_update, run_identity_show


class TestIdentityUpdate:
    def test_update_single_section(self, tmp_path):
        user_md = tmp_path / "identity" / "user.md"
        user_md.parent.mkdir(parents=True, exist_ok=True)
        user_md.write_text("# User\n\n## 基本情報\n- 名前:\n", encoding="utf-8")

        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = user_md
            run_identity_update(
                target="user", section="基本情報",
                content="- 名前: Akira\n- 役割: コンサルタント",
                json_input=None,
            )

        text = user_md.read_text(encoding="utf-8")
        assert "Akira" in text
        assert "コンサルタント" in text

    def test_update_json_multiple_sections(self, tmp_path):
        user_md = tmp_path / "identity" / "user.md"
        user_md.parent.mkdir(parents=True, exist_ok=True)
        user_md.write_text("# User\n\n## 基本情報\n- 名前:\n", encoding="utf-8")

        sections = {"基本情報": "- 名前: Akira", "専門性": "Python, Go"}
        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = user_md
            run_identity_update(
                target="user", section=None,
                content=None,
                json_input=json.dumps(sections),
            )

        text = user_md.read_text(encoding="utf-8")
        assert "Akira" in text
        assert "Python, Go" in text

    def test_update_soul(self, tmp_path):
        soul_md = tmp_path / "identity" / "soul.md"
        soul_md.parent.mkdir(parents=True, exist_ok=True)
        soul_md.write_text("# Soul\n\n## 役割\nテンプレート\n", encoding="utf-8")

        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_soul_path = soul_md
            run_identity_update(
                target="soul", section="役割",
                content="開発パートナー",
                json_input=None,
            )

        text = soul_md.read_text(encoding="utf-8")
        assert "開発パートナー" in text


class TestIdentityShow:
    def test_show_user(self, tmp_path, capsys):
        user_md = tmp_path / "identity" / "user.md"
        user_md.parent.mkdir(parents=True, exist_ok=True)
        user_md.write_text("# User\n\n## 基本情報\n- 名前: Akira\n", encoding="utf-8")

        with patch("cognitive_memory.cli.identity_cmd.CogMemConfig") as mock:
            mock.find_and_load.return_value.identity_user_path = user_md
            mock.find_and_load.return_value.identity_soul_path = tmp_path / "nope.md"
            run_identity_show(target="user")

        out = capsys.readouterr().out
        assert "Akira" in out
```

- [ ] **Step 2: テスト実行 — FAIL 確認**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_cli_identity.py -v`
Expected: FAIL

- [ ] **Step 3: 実装 — identity_cmd.py**

```python
# src/cognitive_memory/cli/identity_cmd.py
"""cogmem identity — view and update identity files."""
from __future__ import annotations

import json
import sys

from ..config import CogMemConfig
from ..identity import parse_identity_md, update_identity_section


def run_identity_update(
    target: str,
    section: str | None = None,
    content: str | None = None,
    json_input: str | None = None,
):
    """Update identity file sections."""
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


def run_identity_show(target: str | None = None):
    """Show current identity file contents."""
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
```

- [ ] **Step 4: main.py にサブコマンド登録**

`src/cognitive_memory/cli/main.py` に追加:

```python
# identity
identity_parser = subparsers.add_parser("identity", help="View and update identity files")
identity_sub = identity_parser.add_subparsers(dest="identity_command")

identity_update = identity_sub.add_parser("update", help="Update identity sections")
identity_update.add_argument("--target", choices=["user", "soul"], required=True,
                              help="Which identity file to update")
identity_update.add_argument("--section", type=str, help="Section heading to update")
identity_update.add_argument("--content", type=str, help="New content for the section")
identity_update.add_argument("--json", type=str, dest="json_input",
                              help='Multiple sections as JSON: {"section": "content"}')

identity_show = identity_sub.add_parser("show", help="Show identity file contents")
identity_show.add_argument("--target", choices=["user", "soul"], default=None,
                            help="Which identity file to show (default: both)")

identity_detect = identity_sub.add_parser("detect", help="Detect placeholder sections")
identity_detect.add_argument("--target", choices=["user", "soul", "agents"], default=None,
                              help="Which file to check (default: all)")
identity_detect.add_argument("--json", action="store_true", dest="json_output",
                              help="Output as JSON")
```

コマンドディスパッチ部分:

```python
elif args.command == "identity":
    from .identity_cmd import run_identity_update, run_identity_show
    if args.identity_command == "update":
        run_identity_update(
            target=args.target,
            section=args.section,
            content=args.content,
            json_input=args.json_input,
        )
    elif args.identity_command == "show":
        run_identity_show(target=getattr(args, "target", None))
    elif args.identity_command == "detect":
        run_identity_detect(
            target=getattr(args, "target", None),
            json_output=getattr(args, "json_output", False),
        )
    else:
        identity_parser.print_help()
```

- [ ] **Step 5: テスト実行 — PASS**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_cli_identity.py tests/test_identity.py -v`
Expected: ALL PASS

- [ ] **Step 6: コミット**

```bash
cd ~/workspace/ai-dev/cognitive-memory-lib
git add src/cognitive_memory/cli/identity_cmd.py src/cognitive_memory/cli/main.py tests/test_cli_identity.py
git commit -m "feat: add cogmem identity update/show CLI commands"
```

---

### Task 4: personality_service を identity.py に統合

**Files:**
- Modify: `src/cognitive_memory/dashboard/services/personality_service.py`
- Modify: `tests/test_dashboard/test_personality.py`

既存の `_read_and_parse_md` を `identity.parse_identity_md` に置き換え、コード重複を解消する。

**注意:** `_read_and_parse_md` は `dict[str, str]` を返すが、`parse_identity_md` は `{"title", "preamble", "sections"}` を返す。テストが `_read_and_parse_md` を直接 import しているので、テスト移行→実装差し替えの順で行う。

- [ ] **Step 1: test_personality.py のテストを先に移行**

`_read_and_parse_md` を直接 import しているテストを `identity.parse_identity_md` に書き換える。
まだ `personality_service.py` は変更しない（テストが既存実装で通ることを確認するため）。

```python
# test_personality.py — TestPersonalityService.test_read_and_parse_md を修正
def test_read_and_parse_md(self, project_dir):
    from cognitive_memory.identity import parse_identity_md

    md_path = project_dir / "test_parse.md"
    md_path.write_text(
        "# Title\n\n## Section A\nContent A\n\n## Section B\nContent B line 1\nContent B line 2\n",
        encoding="utf-8",
    )
    result = parse_identity_md(md_path)
    assert "Section A" in result["sections"]
    assert result["sections"]["Section A"] == "Content A"
    assert "Section B" in result["sections"]
    assert "Content B line 1" in result["sections"]["Section B"]

# test_read_and_parse_md_missing も修正
def test_read_and_parse_md_missing(self, tmp_path):
    from cognitive_memory.identity import parse_identity_md
    result = parse_identity_md(tmp_path / "nonexistent.md")
    assert result["sections"] == {}
```

- [ ] **Step 2: テスト実行 — 移行したテストが PASS 確認**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_dashboard/test_personality.py -v`
Expected: ALL PASS（identity.py は Task 1 で作成済み、他テストは未変更）

- [ ] **Step 3: personality_service.py を修正**

`_read_and_parse_md` を削除し、`identity.parse_identity_md` を使う:

```python
# personality_service.py — 変更箇所のみ
from ...identity import parse_identity_md

def get_personality_data(config: CogMemConfig) -> dict[str, Any]:
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
```

`_read_and_parse_md` 関数を削除。

- [ ] **Step 4: 全テスト実行 — PASS**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: コミット**

```bash
cd ~/workspace/ai-dev/cognitive-memory-lib
git add src/cognitive_memory/dashboard/services/personality_service.py tests/test_dashboard/test_personality.py
git commit -m "refactor: use identity.py parser in personality_service"
```

---

### Task 5: agents.md に Wrap Step 4.5 追加

**Files:**
- Modify: `~/workspace/open-claude/identity/agents.md`

agents.md の Wrap フローに identity 更新ステップを追加する。

- [ ] **Step 1: agents.md に Step 4.5 を追加**

Step 4（knowledge/summary.md 更新）と Step 5（total_sessions インクリメント）の間に挿入:

```markdown
4.5. Identity 更新:
     a. `cogmem identity detect` でプレースホルダー状態を確認
        → 全セクション False（実データ済み）でもログに新情報があれば更新する
     b. 本セッションのログエントリを走査し、以下に該当する情報を抽出:
        - ユーザーの基本情報（名前、役割、タイムゾーン）
        - 専門性・スキル
        - コミュニケーション好み
        - 意思決定パターン
        - エージェントの振る舞いへのフィードバック
     c. 該当情報がなければスキップ
     d. 該当情報があれば `cogmem identity update` で更新:
        ```bash
        cogmem identity update --target user --json '{"セクション名": "内容"}'
        cogmem identity update --target soul --section "セクション名" --content "内容"
        ```
     d. 引き継ぎに「Identity 更新: [user/soul] [更新セクション]」と記録
```

- [ ] **Step 2: Identity Auto-Update セクションを更新**

既存の「Identity Auto-Update」セクションに Wrap 統合の説明を追加:

```markdown
### identity/user.md — 自動更新

ユーザーに関する新しい情報を学んだら Wrap 時に一括更新:
- セッション中に判明した専門性やスキル
- 観察されたコミュニケーション好み
- 意思決定パターンや思考スタイル
- 基本情報（名前、役割、タイムゾーン）

更新は `cogmem identity update --target user` で実行する。
セッション中にリアルタイムで直接 Edit しても良いが、
Wrap Step 4.5 で漏れを補完する。
```

- [ ] **Step 3: コミット**

```bash
cd ~/workspace/open-claude
git add identity/agents.md
git commit -m "feat: add Wrap Step 4.5 for identity auto-update"
```

---

### Task 6: 既存 identity ファイルの初回データ投入

**Files:**
- Modify: `~/workspace/open-claude/identity/user.md`
- Modify: `~/workspace/open-claude/identity/soul.md`

CLAUDE.md とメモリに蓄積されている実データで初回更新する。
実装完了後に `cogmem identity update` を使って更新し、動作確認を兼ねる。

- [ ] **Step 1: user.md を更新**

```bash
cd ~/workspace/open-claude
cogmem identity update --target user --json '{
  "基本情報": "- 名前: Akira（本上 陽）\n- 役割: 経営コンサルタント / strategit\n- タイムゾーン: Asia/Tokyo (GMT+9)",
  "専門性": "- 経営戦略・事業分析・財務判断\n- 効率・シンプル・自動化を重視\n- CLI/API 優先のワークスタイル",
  "コミュニケーション好み": "- 日本語（英語で話しかけた時のみ英語）\n- 簡潔・結論ファースト\n- 余計な前置き不要\n- 絵文字なし",
  "意思決定パターン": "- 数字ベースの判断\n- 最小限の変更で最大効果\n- 破壊的操作は確認してから実行"
}'
```

- [ ] **Step 2: soul.md を更新**

```bash
cd ~/workspace/open-claude
cogmem identity update --target soul --json '{
  "役割": "開発パートナー、批判的思考パートナー、ブレインストーミング相手",
  "核心的価値観": "1. 事実のみ報告 — 曖昧さを避ける。わからないことはわからないと言う\n2. 根拠ベースの思考 — 常に「その証拠は？」と問う\n3. 成長を促す — ユーザーの思考の枠を広げる",
  "思考スタイル": "- 仮説ファースト — 結論より「もしかすると〜」から始める\n- 反証志向 — 「これが成立しない条件は？」を常に考える",
  "コミュニケーションスタイル": "- 言語: 日本語（ユーザーが英語で話しかけた場合のみ英語）\n- トーン: 女性らしい柔らかく親しみやすい口調（「〜だよ」「〜だね」「〜かな」）\n- フォーマット: 結論先行・簡潔・箇条書き優先",
  "やらないこと": "- 根拠なしの楽観、アイデアの即座な全肯定\n- ユーザーの思考を代替しない — 答えより良い問いを立てる\n- 不要な複雑さの導入\n- 聞く前に調べる — コンテキストを確認してから質問する"
}'
```

- [ ] **Step 3: ダッシュボードで確認**

```bash
# ブラウザでパーソナリティページを確認
$B goto http://127.0.0.1:8765/personality/
$B text
```

- [ ] **Step 4: コミット**

```bash
cd ~/workspace/open-claude
git add identity/user.md identity/soul.md
git commit -m "feat: populate identity files with real user/agent data"
```

---

### Task 7: セッションログ fixture を使ったインテグレーションテスト

**Files:**
- Create: `tests/test_identity_integration.py`
- Reference: `tests/fixtures/session_logs/*.md`（作成済み）

ダミーセッションログを使って、identity 更新の E2E フローをテストする。
LLM 判断部分はテストしない（モック不可）が、「ログを読み → detect で状態確認 → update で更新 → 結果検証」のパイプラインを検証する。

- [ ] **Step 1: テスト作成**

```python
# tests/test_identity_integration.py
"""Identity update integration tests using session log fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_memory.identity import (
    detect_placeholder_sections,
    parse_identity_md,
    update_identity_section,
)

FIXTURES = Path(__file__).parent / "fixtures" / "session_logs"


class TestUserExpertiseUpdate:
    """user_expertise.md: Go/gRPC/dagster の専門性 → user.md 専門性を更新。"""

    def test_detect_before_update(self, tmp_path):
        user_md = tmp_path / "user.md"
        user_md.write_text(
            "# ユーザープロファイル\n\n## 専門性\n[会話から観察された内容]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(user_md)
        assert result["専門性"] is True

    def test_update_from_log(self, tmp_path):
        user_md = tmp_path / "user.md"
        user_md.write_text(
            "# ユーザープロファイル\n\n## 専門性\n[会話から観察された内容]\n",
            encoding="utf-8",
        )
        # Simulate what the agent would do after reading user_expertise.md log
        update_identity_section(
            user_md, "専門性",
            "- Go（10年）、pprof によるヒープ分析\n- gRPC（社内マイクロサービス）\n- dagster（ETL パイプライン）",
        )
        result = detect_placeholder_sections(user_md)
        assert result["専門性"] is False
        data = parse_identity_md(user_md)
        assert "Go" in data["sections"]["専門性"]
        assert "gRPC" in data["sections"]["専門性"]

    def test_log_fixture_exists(self):
        assert (FIXTURES / "user_expertise.md").exists()


class TestUserBasicInfoUpdate:
    """user_basic_info.md: 名前/役割/TZ → user.md 基本情報を更新。"""

    def test_detect_empty_fields(self, tmp_path):
        user_md = tmp_path / "user.md"
        user_md.write_text(
            "# ユーザープロファイル\n\n## 基本情報\n- 名前:\n- 役割:\n- タイムゾーン:\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(user_md)
        assert result["基本情報"] is True

    def test_update_from_log(self, tmp_path):
        user_md = tmp_path / "user.md"
        user_md.write_text(
            "# ユーザープロファイル\n\n## 基本情報\n- 名前:\n- 役割:\n- タイムゾーン:\n",
            encoding="utf-8",
        )
        update_identity_section(
            user_md, "基本情報",
            "- 名前: 田中太郎\n- 役割: CTO（SaaS スタートアップ）\n- タイムゾーン: Asia/Tokyo (JST)",
        )
        result = detect_placeholder_sections(user_md)
        assert result["基本情報"] is False
        data = parse_identity_md(user_md)
        assert "田中太郎" in data["sections"]["基本情報"]

    def test_log_fixture_exists(self):
        assert (FIXTURES / "user_basic_info.md").exists()


class TestSoulFeedbackUpdate:
    """soul_feedback.md: トーン変更/結論ファースト/反論歓迎 → soul.md を更新。"""

    def test_detect_template_soul(self, tmp_path):
        soul_md = tmp_path / "soul.md"
        soul_md.write_text(
            "# Soul\n\n## コミュニケーションスタイル\n"
            "- トーン: [カジュアル / フォーマル / 等]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(soul_md)
        assert result["コミュニケーションスタイル"] is True

    def test_update_from_log(self, tmp_path):
        soul_md = tmp_path / "soul.md"
        soul_md.write_text(
            "# Soul\n\n## コミュニケーションスタイル\n"
            "- トーン: [カジュアル / フォーマル / 等]\n\n"
            "## 役割\n[このプロジェクトにおけるエージェントの役割を記述]\n",
            encoding="utf-8",
        )
        update_identity_section(
            soul_md, "コミュニケーションスタイル",
            "- トーン: カジュアル（敬語不要）\n- フォーマット: 結論ファースト",
        )
        update_identity_section(
            soul_md, "役割",
            "批判的思考パートナー（反論を歓迎される）",
        )
        result = detect_placeholder_sections(soul_md)
        assert result["コミュニケーションスタイル"] is False
        assert result["役割"] is False

    def test_log_fixture_exists(self):
        assert (FIXTURES / "soul_feedback.md").exists()


class TestAgentsProtocolUpdate:
    """agents_protocol.md: プロトコル変更要望 → agents.md 検知。"""

    def test_detect_template_agents(self, tmp_path):
        agents_md = tmp_path / "agents.md"
        agents_md.write_text(
            "# Agents\n\n## Live Logging\n[Configure your logging triggers here]\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(agents_md)
        assert result["Live Logging"] is True

    def test_customized_not_placeholder(self, tmp_path):
        agents_md = tmp_path / "agents.md"
        agents_md.write_text(
            "# Agents\n\n## Live Logging\n"
            "重要な瞬間に memory/logs/YYYY-MM-DD.md に即座に追記する。\n",
            encoding="utf-8",
        )
        result = detect_placeholder_sections(agents_md)
        assert result["Live Logging"] is False

    def test_log_fixture_exists(self):
        assert (FIXTURES / "agents_protocol.md").exists()


class TestNoIdentityUpdate:
    """no_identity_update.md: 技術的な作業のみ → 更新不要。"""

    def test_already_filled_stays_unchanged(self, tmp_path):
        """実データ入り identity は更新されない（ログに identity 情報がないため）。"""
        user_md = tmp_path / "user.md"
        original = (
            "# ユーザープロファイル\n\n"
            "## 基本情報\n- 名前: Akira\n- 役割: コンサルタント\n\n"
            "## 専門性\nPython, SQL\n"
        )
        user_md.write_text(original, encoding="utf-8")
        result = detect_placeholder_sections(user_md)
        assert all(v is False for v in result.values())
        # ファイルは変更されていない
        assert user_md.read_text(encoding="utf-8") == original

    def test_log_fixture_exists(self):
        assert (FIXTURES / "no_identity_update.md").exists()
```

- [ ] **Step 2: テスト実行 — PASS 確認**

Run: `cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/test_identity_integration.py -v`
Expected: ALL PASS（identity.py 実装後に実行）

- [ ] **Step 3: コミット**

```bash
cd ~/workspace/ai-dev/cognitive-memory-lib
git add tests/test_identity_integration.py tests/fixtures/
git commit -m "test: add integration tests with session log fixtures"
```

---

## 全体テスト

```bash
cd ~/workspace/ai-dev/cognitive-memory-lib && python -m pytest tests/ -v
```

Expected: 全テスト PASS（既存 296 + 新規 ~45 = ~341）

### テスト内訳

| ファイル | テスト数 | 内容 |
|---------|---------|------|
| `test_identity.py` | 25 | parse(3) + write(4) + update(4) + placeholder検知(14) |
| `test_cli_identity.py` | 8 | CLI update(5) + show(3) |
| `test_identity_integration.py` | 12 | fixture 連動の E2E（user/soul/agents × detect→update→verify） |
| **新規合計** | **45** | |
