"""Skills service for dashboard views."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import List, Optional

from ...config import CogMemConfig
from ...skills.store import SkillsStore
from ...skills.audit import SkillAuditor

# Common locations for .claude/skills/
_CLAUDE_SKILLS_DIRS = [
    Path.home() / ".claude" / "skills",
]

_PLUGINS_JSON = Path.home() / ".claude" / "plugins" / "installed_plugins.json"


def get_update_status(config: CogMemConfig) -> dict[str, dict]:
    """Read skill update cache written by `cogmem skills check-updates`."""
    cache_path = Path(config._base_dir) / "memory" / "skill-updates.json"
    if not cache_path.exists():
        return {}
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        return data.get("sources", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _get_source_versions() -> dict[str, str]:
    """Read version from package.json in source directories under .claude/skills/."""
    versions: dict[str, str] = {}
    for skills_dir in _CLAUDE_SKILLS_DIRS:
        if not skills_dir.exists():
            continue
        for entry in skills_dir.iterdir():
            if not entry.is_dir() or not entry.name in versions:
                pkg = entry / "package.json"
                if pkg.exists():
                    try:
                        data = json.loads(pkg.read_text(encoding="utf-8"))
                        versions[entry.name] = data.get("version", "")
                    except (json.JSONDecodeError, OSError):
                        pass
    return versions


def _scan_claude_skills() -> dict[str, dict]:
    """Scan .claude/skills/ directories for user's own skill metadata.

    Excludes: agency-* (marketplace), symlinks (gstack/superpowers), learned/, __pycache__
    """
    source_versions = _get_source_versions()
    skills = {}
    for skills_dir in _CLAUDE_SKILLS_DIRS:
        if not skills_dir.exists():
            continue
        for entry in skills_dir.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            # Skip marketplace/framework/internal directories
            if entry.name.startswith("agency-"):
                continue
            if entry.name in ("learned", "gstack", "__pycache__"):
                continue
            skill_file = entry / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                text = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            # Parse YAML frontmatter
            fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not fm_match:
                continue
            fm = fm_match.group(1)
            name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
            desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
            if name_match:
                skill_name = name_match.group(1).strip()
                # Handle YAML multiline literal (description: |)
                desc = ""
                if desc_match:
                    raw = desc_match.group(1).strip()
                    if raw == "|" or raw == ">":
                        # Collect indented continuation lines
                        desc_block = re.search(
                            r"^description:\s*[|>]\s*\n((?:[ \t]+.+\n?)+)",
                            fm, re.MULTILINE,
                        )
                        if desc_block:
                            lines = desc_block.group(1).strip().splitlines()
                            desc = " ".join(l.strip() for l in lines)
                    else:
                        desc = raw
                # Determine source for symlinked skills
                source = ""
                source_version = ""
                is_symlink = entry.is_symlink()
                if is_symlink:
                    target = str(entry.readlink())
                    if target.startswith("gstack/"):
                        source = "gstack"
                    elif "cognitive-memory" in target or "cogmem" in target:
                        source = "cogmem"
                    else:
                        source = target.split("/")[0] or "external"
                    source_version = source_versions.get(source, "")
                # Per-skill version from frontmatter
                ver_match = re.search(r"^version:\s*(.+)$", fm, re.MULTILINE)
                skill_version = ver_match.group(1).strip() if ver_match else ""
                # Japanese description
                desc_ja_match = re.search(r"^description_ja:\s*(.+)$", fm, re.MULTILINE)
                desc_ja = desc_ja_match.group(1).strip().strip('"').strip("'") if desc_ja_match else ""
                if not desc_ja:
                    desc_ja = _SKILL_DESC_JA.get(skill_name, "")
                skills[skill_name] = {
                    "name": skill_name,
                    "description": desc,
                    "description_ja": desc_ja,
                    "path": str(skill_file),
                    "improvable": not is_symlink or source == "cogmem",
                    "source": source,
                    "source_version": source_version,
                    "skill_version": skill_version,
                }
    return skills


# Built-in Japanese descriptions for skills without description_ja
_SKILL_DESC_JA: dict[str, str] = {
    # Plugins
    "brainstorming": "創造的な作業の前にアイデアをデザインに発展させる対話型ブレスト",
    "dispatching-parallel-agents": "独立した複数タスクを並列エージェントに分散実行",
    "executing-plans": "実装プランをステップごとに順次実行",
    "finishing-a-development-branch": "実装完了後のブランチ整理とマージ準備",
    "receiving-code-review": "コードレビューのフィードバックを受けて修正を実施",
    "requesting-code-review": "完了したタスクのコードレビューを依頼",
    "subagent-driven-development": "タスクごとにサブエージェントを起動し2段階レビュー付きで実装",
    "systematic-debugging": "バグや予期しない動作を体系的に根本原因まで調査",
    "test-driven-development": "テスト駆動開発（TDD）で実装を進める",
    "using-git-worktrees": "git worktreeで機能ブランチを隔離して作業",
    "using-superpowers": "スキルの検索と適用方法を確立する導入スキル",
    "verification-before-completion": "完了報告前に実際の動作を検証して確認",
    "writing-plans": "仕様から詳細な実装プランを作成",
    "writing-skills": "新しいスキルの作成・既存スキルの改善",
    "frontend-design": "プロダクション品質のフロントエンドUIを設計・実装",
    "skill-creator": "スキルの新規作成・改善・ベンチマーク測定",
    # Improvable (user-created)
    "context-architecture": "新しい情報の保存先やメモリ構造の設計を判断するスキル",
    "content-workflow": "ブレスト・コンテンツ作成・複数URL取得などの創作ワークフロー",
    "cmux-browser": "cmux上でブラウザ自動操作を行うスキル",
    "cmux-read-screen": "cmux上のターミナル出力を読み取るスキル",
    "cmux-markdown": "マークダウンをフォーマット付きビューアパネルで表示",
    "cmux": "cmuxのトポロジー制御（ウィンドウ・ワークスペース・ペイン管理）",
    # External (gstack)
    "benchmark": "パフォーマンス回帰検出。ページロード時間・Core Web Vitals・リソースサイズを計測",
    "design-shotgun": "複数のAIデザインバリアントを生成し比較レビュー",
    "design-consultation": "プロダクトを理解し、リサーチに基づくデザインコンサルティング",
    "freeze": "セッション中の編集対象を特定ディレクトリに制限",
    "careful": "破壊的コマンドに対する安全ガードレール",
    "cso": "インフラ優先のセキュリティ監査モード",
    "canary": "デプロイ後のカナリアモニタリング（コンソールエラー・API障害監視）",
    "investigate": "根本原因調査による体系的デバッグ（4フェーズ）",
    "document-release": "リリース後のドキュメント更新（全プロジェクトドキュメントを横断確認）",
    "gstack-upgrade": "gstackを最新バージョンにアップグレード",
    "land-and-deploy": "PRマージ・CI待機・デプロイのワークフロー",
    "qa": "Webアプリの体系的QAテストとバグ修正",
    "qa-only": "レポートのみのQAテスト（修正なし）",
    "setup-browser-cookies": "実ブラウザのCookieをヘッドレスブラウザにインポート",
    "review": "PRランディング前のコードレビュー（diff解析）",
    "plan-ceo-review": "CEO/創業者視点でのプランレビュー（10x思考）",
    "retro": "週次エンジニアリング振り返り（コミット・ワークフロー分析）",
    "connect-chrome": "gstackサイドパネル付きのChrome起動・制御",
    "browse": "QAテスト・サイト確認用の高速ヘッドレスブラウザ",
    "design-review": "デザイナー視点のQA（スペーシング・配色・一貫性チェック）",
    "ship": "出荷ワークフロー（ベースブランチマージ・テスト・レビュー・diff）",
    "guard": "フルセーフティモード（破壊コマンド警告＋ディレクトリ制限）",
    "unfreeze": "freezeで設定したディレクトリ制限を解除",
    "setup-deploy": "デプロイ設定の構成（/land-and-deploy用）",
    "codex": "OpenAI Codex CLIラッパー（コードレビュー・独立モード）",
    "office-hours": "YCオフィスアワー形式（スタートアップ向け強制質問）",
    "plan-design-review": "デザイナー視点のプランレビュー",
    "plan-eng-review": "エンジニアリングマネージャー視点のプランレビュー",
    "autoplan": "CEO・デザイン・エンジニアリングレビューの自動パイプライン",
}


def _parse_skill_description(fm: str) -> str:
    """Extract description from YAML frontmatter, handling multiline literals."""
    desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
    if not desc_match:
        return ""
    raw = desc_match.group(1).strip().strip('"').strip("'")
    if raw in ("|", ">"):
        desc_block = re.search(
            r"^description:\s*[|>]\s*\n((?:[ \t]+.+\n?)+)",
            fm, re.MULTILINE,
        )
        if desc_block:
            lines = desc_block.group(1).strip().splitlines()
            return " ".join(l.strip() for l in lines)
        return ""
    return raw


def get_plugin_skills(config: CogMemConfig | None = None) -> list[dict]:
    """Scan installed Claude Code plugins for skills."""
    if not _PLUGINS_JSON.exists():
        return []
    try:
        data = json.loads(_PLUGINS_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    # Load update cache for version comparison
    update_sources: dict[str, dict] = {}
    if config:
        update_sources = get_update_status(config)

    plugins = data.get("plugins", {})
    result: list[dict] = []
    seen: set[str] = set()

    for plugin_key, installs in plugins.items():
        # plugin_key = "superpowers@superpowers-marketplace"
        plugin_name = plugin_key.split("@")[0]
        for install in installs:
            install_path = Path(install.get("installPath", ""))
            skills_dir = install_path / "skills"
            if not skills_dir.exists():
                continue
            version = install.get("version", "")
            # Get update info from cache
            pinfo = update_sources.get(f"plugin:{plugin_name}", {})
            latest_version = pinfo.get("latest_version", "")
            up_to_date = pinfo.get("up_to_date", True)

            for entry in skills_dir.iterdir():
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                skill_file = entry / "SKILL.md"
                if not skill_file.exists():
                    continue
                if entry.name in seen:
                    continue
                seen.add(entry.name)
                try:
                    text = skill_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
                if not fm_match:
                    continue
                fm = fm_match.group(1)
                name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
                if not name_match:
                    continue
                skill_name = name_match.group(1).strip()
                desc_en = _parse_skill_description(fm)
                # Check for Japanese description
                desc_ja_match = re.search(r"^description_ja:\s*(.+)$", fm, re.MULTILINE)
                desc_ja = ""
                if desc_ja_match:
                    raw_ja = desc_ja_match.group(1).strip().strip('"').strip("'")
                    desc_ja = raw_ja
                if not desc_ja:
                    desc_ja = _SKILL_DESC_JA.get(skill_name, "")
                result.append({
                    "name": skill_name,
                    "description": desc_en,
                    "description_ja": desc_ja,
                    "plugin": plugin_name,
                    "version": version,
                    "latest_version": latest_version,
                    "up_to_date": up_to_date,
                })
    result.sort(key=lambda s: s["name"])
    return result


def _get_event_stats(config: CogMemConfig) -> dict[str, dict]:
    """Get per-skill event stats from skill_session_events table."""
    db_path = Path(config._base_dir) / "memory" / "skills.db"
    if not db_path.exists():
        return {}
    stats: dict[str, dict] = {}
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT skill_name, event_type, COUNT(*) as cnt, "
            "MAX(timestamp) as last_ts "
            "FROM skill_session_events "
            "GROUP BY skill_name, event_type"
        ).fetchall()
        for r in rows:
            name = r["skill_name"]
            if name not in stats:
                stats[name] = {"total_events": 0, "last_used": None, "events_by_type": {}}
            stats[name]["total_events"] += r["cnt"]
            stats[name]["events_by_type"][r["event_type"]] = r["cnt"]
            if stats[name]["last_used"] is None or r["last_ts"] > stats[name]["last_used"]:
                stats[name]["last_used"] = r["last_ts"]
        conn.close()
    except sqlite3.Error:
        pass
    return stats


def _load_db_skills(config: CogMemConfig) -> list[dict]:
    """Load all DB skills directly from SQLite with claude_skill_name mapping.

    Reads the skills table. Adds claude_skill_name column if missing (migration).
    """
    db_path = Path(config._base_dir) / "memory" / "skills.db"
    if not db_path.exists():
        return []
    result: list[dict] = []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Migration: add claude_skill_name column if missing
        try:
            conn.execute("ALTER TABLE skills ADD COLUMN claude_skill_name TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists

        rows = conn.execute(
            "SELECT id, name, category, description, average_effectiveness, "
            "total_executions, last_used_at, version, claude_skill_name FROM skills"
        ).fetchall()
        for row in rows:
            # Get usage log for trend
            usage_rows = conn.execute(
                "SELECT effectiveness FROM skill_usage_log "
                "WHERE skill_id = ? ORDER BY timestamp DESC LIMIT 5",
                (row["id"],),
            ).fetchall()
            effs = [r["effectiveness"] for r in usage_rows if r["effectiveness"] is not None]
            result.append({
                "id": row["id"],
                "claude_skill_name": row["claude_skill_name"],
                "category": row["category"],
                "effectiveness": row["average_effectiveness"],
                "total_executions": row["total_executions"],
                "last_used_at": row["last_used_at"],
                "trend": _determine_trend(effs),
                "version": row["version"],
                "improvements": max(0, row["version"] - 1),
            })
        conn.close()
    except sqlite3.Error:
        pass
    return result


def get_skills_list(config: CogMemConfig) -> list:
    """Get skills from .claude/skills/ enriched with cogmem DB stats.

    Matching priority:
    1. DB skill id == .claude/skills/ directory name (exact)
    2. DB claude_skill_name == .claude/skills/ directory name
    """
    claude_skills = _scan_claude_skills()
    event_stats = _get_event_stats(config)
    db_skills = _load_db_skills(config)
    matched_ids: set = set()

    result = []
    for skill_name, meta in claude_skills.items():
        events = event_stats.get(skill_name, {})

        # Match: exact id, then claude_skill_name column
        db = None
        for d in db_skills:
            if d["id"] in matched_ids:
                continue
            if d["id"] == skill_name or d.get("claude_skill_name") == skill_name:
                db = d
                matched_ids.add(d["id"])
                break

        result.append({
            "id": skill_name,
            "name": skill_name,
            "summary": meta["description"],
            "summary_ja": meta.get("description_ja", ""),
            "description": meta["description"],
            "category": db["category"] if db else "—",
            "effectiveness": db["effectiveness"] if db else 0.0,
            "total_executions": db["total_executions"] if db else 0,
            "total_events": events.get("total_events", 0),
            "last_used_at": (db["last_used_at"] if db else None) or events.get("last_used"),
            "trend": db["trend"] if db else "new",
            "version": db["version"] if db else _parse_version(meta.get("skill_version", "")),
            "improvements": db["improvements"] if db else max(0, _parse_version(meta.get("skill_version", "")) - 1),
            "events_by_type": events.get("events_by_type", {}),
            "improvable": meta.get("improvable", False),
            "source": meta.get("source", ""),
            "source_version": meta.get("source_version", ""),
            "skill_version": meta.get("skill_version", ""),
        })

    result.sort(key=lambda s: s["total_executions"], reverse=True)
    return result


def _parse_version(ver_str: str) -> int:
    """Parse version string (e.g. '3.0.0') to major version int."""
    if not ver_str:
        return 1
    try:
        return int(ver_str.split(".")[0])
    except (ValueError, IndexError):
        return 1


def _determine_trend(effs: list) -> str:
    """Determine trend from effectiveness values (newest first)."""
    if len(effs) < 3:
        return "new"
    if len(effs) >= 5:
        is_increasing = all(effs[i] > effs[i + 1] for i in range(len(effs) - 1))
        if is_increasing:
            return "up"
        is_decreasing = all(effs[i] < effs[i + 1] for i in range(len(effs) - 1))
        if is_decreasing:
            return "down"
    return "flat"


def get_skill_detail(config: CogMemConfig, skill_id: str) -> Optional[dict]:
    """Get skill detail with usage log and events.

    Returns {skill: Skill, usage_log: list, events: list} or None.
    """
    store = SkillsStore(config)
    all_skills = store.load_all_skills()

    skill = None
    for category_skills in all_skills.values():
        for s in category_skills:
            if s.id == skill_id:
                skill = s
                break
        if skill:
            break

    if skill is None:
        return None

    usage_log = store.get_recent_usage_log(skill.id, 20)

    events: list = []
    try:
        with sqlite3.connect(store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT session_date, skill_name, event_type, description, "
                "step_ref, timestamp FROM skill_session_events "
                "WHERE skill_name = ? ORDER BY timestamp DESC",
                (skill.name,),
            ).fetchall()
            events = [dict(r) for r in rows]
    except Exception:
        pass

    return {
        "skill": skill,
        "usage_log": usage_log,
        "events": events,
    }


def get_skill_trend(config: CogMemConfig, skill_id: str) -> list:
    """Get effectiveness data points for chart.

    Returns list of {timestamp, effectiveness} from skill_usage_log.
    """
    store = SkillsStore(config)
    log = store.get_recent_usage_log(skill_id, 50)
    return [
        {"timestamp": e["timestamp"], "effectiveness": e["effectiveness"]}
        for e in reversed(log)
        if e["effectiveness"] is not None
    ]


def get_audit_results(config: CogMemConfig) -> dict:
    """Run SkillAuditor.audit() and return results."""
    store = SkillsStore(config)
    auditor = SkillAuditor(store)
    result = auditor.audit()

    # Add auto-improvement stats
    db_path = Path(config._base_dir) / "memory" / "skills.db"
    total_improvements = 0
    unresolved_events = 0
    auto_created = 0
    pending_suggestions = 0
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            row = conn.execute(
                "SELECT COUNT(*) FROM skill_session_events WHERE resolved = 1"
            ).fetchone()
            total_improvements = row[0] if row else 0
            row2 = conn.execute(
                "SELECT COUNT(*) FROM skill_session_events WHERE resolved = 0"
            ).fetchone()
            unresolved_events = row2[0] if row2 else 0
            row3 = conn.execute(
                "SELECT COUNT(DISTINCT context) FROM skill_suggestions WHERE promoted = 1"
            ).fetchone()
            auto_created = row3[0] if row3 else 0
            row4 = conn.execute(
                "SELECT COUNT(DISTINCT context) FROM skill_suggestions WHERE promoted = 0"
            ).fetchone()
            pending_suggestions = row4[0] if row4 else 0
            conn.close()
        except sqlite3.Error:
            pass
    result["summary"]["total_improvements"] = total_improvements
    result["summary"]["unresolved_events"] = unresolved_events
    result["summary"]["auto_created"] = auto_created
    result["summary"]["pending_suggestions"] = pending_suggestions
    # Override total_skills with improvable skills count only (exclude external)
    claude_skills = _scan_claude_skills()
    result["summary"]["total_skills"] = sum(
        1 for s in claude_skills.values() if s.get("improvable", False)
    )
    return result
