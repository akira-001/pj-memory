"""Shared fixtures for dashboard tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from cognitive_memory.config import CogMemConfig
from cognitive_memory.dashboard import create_app

try:
    from httpx import ASGITransport, AsyncClient
except ImportError:
    ASGITransport = None
    AsyncClient = None

SAMPLE_LOG = """\
# 2026-03-20 セッションログ

## セッション概要
テストセッションの概要です。

## ログエントリ

### [INSIGHT] テスト洞察
*Arousal: 0.8 | Emotion: Discovery*
これはテスト用の洞察エントリです。

---

### [DECISION] テスト決定
*Arousal: 0.6 | Emotion: Clarity*
これはテスト用の決定エントリです。

---

### [ERROR] テストエラー
*Arousal: 0.9 | Emotion: Correction*
これはテスト用のエラーエントリです。

---

## 引き継ぎ
- **継続テーマ**: テスト
- **次のアクション**: テスト完了
"""

# --- Crystallization test data ---

# Log with multiple PATTERN/ERROR entries (triggers crystallization signals)
SAMPLE_LOG_PATTERNS = """\
# 2026-03-18 セッションログ

## セッション概要
パターンとエラーが多いセッション。

## ログエントリ

### [PATTERN] 同じミスを繰り返す
*Arousal: 0.7 | Emotion: Self-awareness*
テスト修正→別のテスト壊す→修正のループ。

---

### [PATTERN] ログ記録を忘れる
*Arousal: 0.7 | Emotion: Self-awareness*
Live Logging を実行し忘れた。

---

### [PATTERN] 浅い探索で見落とす
*Arousal: 0.8 | Emotion: Frustration*
ルートディレクトリを確認せずに結論を出した。

---

### [ERROR] cwd 依存で間違った DB を読んだ
*Arousal: 0.8 | Emotion: Correction*
pip install で cwd が移動した。

---

### [ERROR] テストが表層しか検証しない
*Arousal: 0.9 | Emotion: Correction*
HTTP 200 だけ見てセル値を検証していなかった。

---

## 引き継ぎ
- **継続テーマ**: パターン修正
"""

SAMPLE_LOG_MORE_ERRORS = """\
# 2026-03-19 セッションログ

## セッション概要
追加エラーのセッション。

## ログエントリ

### [ERROR] 環境要因を見落とした
*Arousal: 0.6 | Emotion: Correction*
コードバグと決めつけたがメモリ枯渇が原因だった。

---

### [ERROR] ID 体系の不一致
*Arousal: 0.8 | Emotion: Frustration*
DB のハッシュ ID と .claude/skills/ のディレクトリ名が一致しない。

---

### [ERROR] 浅い探索で skill-creator を見落とした
*Arousal: 0.8 | Emotion: Correction*
marketplaces/ を見落とした。

---

### [INSIGHT] スキル管理の3層構造
*Arousal: 0.7 | Emotion: Clarity*
マッチング、学習、作成の3層に整理できた。

---

## 引き継ぎ
- **継続テーマ**: エラーパターン整理
"""

# Error patterns file with 3 entries
SAMPLE_ERROR_PATTERNS = """\
# エラーパターン

*結晶化プロセスで更新されます。最終更新: 2026-03-26*

---

## EP-001: 浅い探索で存在するリソースを見落とす
**発生**: 2026-03-25 | **Arousal**: 0.8
**パターン**: ディレクトリの一部だけ見て「これで全部」と判断する。
**対策**: `/exhaustive-exploration` スキルを使う。

## EP-002: テストが表層しか検証しない
**発生**: 2026-03-25 | **Arousal**: 0.9
**パターン**: HTTP 200 + キーワード存在だけ確認し、実際の表示内容を検証しない。
**対策**: HTML 出力に対して実データを検証する。

## EP-003: cwd 依存で間違ったデータを読む
**発生**: 2026-03-25 | **Arousal**: 0.8
**パターン**: pip install 等で cwd が移動し、別プロジェクトの cogmem.toml を読む。
**対策**: cogmem コマンドは必ず正しいディレクトリから実行する。
"""

# Error patterns file with empty template
SAMPLE_ERROR_PATTERNS_EMPTY = """\
# エラーパターン

*繰り返すミスのパターン。結晶化時に更新されます。*

[まだパターンは記録されていません]
"""

# Knowledge summary with 3 principles
SAMPLE_KNOWLEDGE_SUMMARY = """\
# 知識サマリー

*最終更新: 2026-03-26（初回結晶化）*

---

## 確立された判断原則

### 1. 探索は網羅的に、検証は実データで
浅い探索で早合点しない。テストは実際の値を検証する。

### 2. 環境要因を先に排除する
表示やパフォーマンスの問題はコードバグと決めつけず、環境状態を先に確認する。

### 3. 実装に集中するとプロトコルを忘れる
cogmem watch + Wrap 遡及チェックで機械的に漏れを検知・補完する。

## エラーパターン
→ 詳細は `error-patterns.md` 参照（EP-001〜EP-003）

## アクティブプロジェクト

### cogmem-agent
- **状態**: v0.8.0 リリース済み
"""

# Knowledge summary with empty template
SAMPLE_KNOWLEDGE_SUMMARY_EMPTY = """\
# 知識サマリー

*結晶化プロセスで更新されます。手動編集も可能です。*
*最終更新: [日付]*

---

## 確立された判断原則
[繰り返し確認された意思決定の原則]

## エラーパターン
→ 詳細は `error-patterns.md` 参照

## アクティブプロジェクト
[進行中のプロジェクトと次のアクション]
"""

# cogmem.toml with crystallization section (checkpoint done)
COGMEM_TOML_WITH_CRYSTALLIZATION = """\
[cogmem]
logs_dir = "memory/logs"
db_path = "memory/vectors.db"

[cogmem.knowledge]
summary = "memory/knowledge/summary.md"
error_patterns = "memory/knowledge/error-patterns.md"

[cogmem.crystallization]
pattern_threshold = 3
error_threshold = 5
log_days_threshold = 10
checkpoint_interval_days = 21
last_checkpoint = "2026-03-26"
checkpoint_count = 1
"""

# cogmem.toml with no checkpoint (never crystallized)
COGMEM_TOML_NEVER_CRYSTALLIZED = """\
[cogmem]
logs_dir = "memory/logs"
db_path = "memory/vectors.db"

[cogmem.knowledge]
summary = "memory/knowledge/summary.md"
error_patterns = "memory/knowledge/error-patterns.md"

[cogmem.crystallization]
pattern_threshold = 3
error_threshold = 5
log_days_threshold = 10
checkpoint_interval_days = 21
last_checkpoint = ""
checkpoint_count = 0
"""

# cogmem.toml for boundary test (just below thresholds)
COGMEM_TOML_BOUNDARY = """\
[cogmem]
logs_dir = "memory/logs"
db_path = "memory/vectors.db"

[cogmem.knowledge]
summary = "memory/knowledge/summary.md"
error_patterns = "memory/knowledge/error-patterns.md"

[cogmem.crystallization]
pattern_threshold = 3
error_threshold = 5
log_days_threshold = 10
checkpoint_interval_days = 21
last_checkpoint = "2026-03-25"
checkpoint_count = 3
"""


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal cogmem project with sample data."""
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)

    # Write sample log
    (logs_dir / "2026-03-20.md").write_text(SAMPLE_LOG, encoding="utf-8")

    # Compact-only log (compacted status)
    (logs_dir / "2026-03-18.compact.md").write_text(
        "# 2026-03-18 コンパクトログ\n"
        "*元ログ: 2026-03-18.md | 圧縮率: 50%*\n\n"
        "## エッセンス\nコンパクトテストの概要です。\n\n"
        "## 重要エントリ\n\n"
        "### [MILESTONE] テストマイルストーン\nマイルストーン内容。\n\n"
        "- [INSIGHT] コンパクト洞察エントリ\n"
        "- [DECISION] コンパクト決定エントリ\n",
        encoding="utf-8",
    )

    # Retained log (both .md and .compact.md exist)
    (logs_dir / "2026-03-19.md").write_text(SAMPLE_LOG_MORE_ERRORS, encoding="utf-8")
    (logs_dir / "2026-03-19.compact.md").write_text(
        "# 2026-03-19 コンパクトログ\n"
        "*元ログ: 2026-03-19.md | 圧縮率: 40%*\n\n"
        "## エッセンス\n追加エラーの圧縮版。\n\n"
        "- [ERROR] 環境要因見落とし\n",
        encoding="utf-8",
    )

    # Write cogmem.toml
    (tmp_path / "cogmem.toml").write_text(
        '[cogmem]\nlogs_dir = "memory/logs"\ndb_path = "memory/vectors.db"\n',
        encoding="utf-8",
    )

    # Create vectors.db with sample data
    db_path = tmp_path / "memory" / "vectors.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY,
            content_hash TEXT UNIQUE,
            date TEXT,
            content TEXT,
            arousal REAL,
            vector BLOB
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indexed_files (
            filename TEXT PRIMARY KEY,
            indexed_at TEXT,
            entry_count INTEGER
        )
    """)

    # Insert sample memories
    memories = [
        ("h1", "2026-03-20", "### [INSIGHT] テスト洞察\n*Arousal: 0.8*\nテスト内容", 0.8, "[]"),
        ("h2", "2026-03-20", "### [DECISION] テスト決定\n*Arousal: 0.6*\nテスト内容", 0.6, "[]"),
        ("h3", "2026-03-20", "### [ERROR] テストエラー\n*Arousal: 0.9*\nテスト内容", 0.9, "[]"),
        ("h4", "2026-03-19", "### [PATTERN] テストパターン\n*Arousal: 0.7*\nテスト内容", 0.7, "[]"),
        ("h5", "2026-03-19", "### [MILESTONE] テストマイルストーン\n*Arousal: 0.6*\nテスト内容", 0.6, "[]"),
    ]
    conn.executemany(
        "INSERT INTO memories (content_hash, date, content, arousal, vector) VALUES (?, ?, ?, ?, ?)",
        memories,
    )
    conn.execute(
        "INSERT INTO indexed_files (filename, indexed_at, entry_count) VALUES (?, ?, ?)",
        ("2026-03-20.md", "2026-03-20T10:00:00", 3),
    )
    conn.commit()
    conn.close()

    # Create skills directory structure with sample skill
    skills_dir = tmp_path / "memory" / "skills"
    for cat in [
        "conversation-skills",
        "proactive-skills",
        "automation-skills",
        "learning-skills",
        "meta-skills",
    ]:
        (skills_dir / cat).mkdir(parents=True)

    # Write sample skill JSON
    sample_skill = {
        "id": "test-skill-001",
        "name": "Test Skill",
        "category": "conversation-skills",
        "description": "A test skill for dashboard testing",
        "execution_pattern": "When testing dashboard, verify all pages render",
        "success_metrics": [
            {
                "name": "render_success",
                "description": "Page renders without error",
                "measurement_method": "http_status == 200",
                "target_value": 1.0,
                "current_value": 1.0,
            }
        ],
        "improvement_history": [],
        "usage_stats": {
            "total_executions": 10,
            "successful_executions": 8,
            "average_effectiveness": 0.75,
            "last_used_at": "2026-03-20T10:00:00",
            "frequency": 0.5,
        },
        "created_at": "2026-03-10T00:00:00",
        "updated_at": "2026-03-20T10:00:00",
        "version": 2,
    }
    (skills_dir / "conversation-skills" / "test-skill-001.json").write_text(
        json.dumps(sample_skill, indent=2), encoding="utf-8"
    )

    # --- Create .claude/skills/ with test skills ---
    claude_skills_dir = tmp_path / ".claude" / "skills"

    # Skill A: high effectiveness, many executions, trending up
    skill_a_dir = claude_skills_dir / "skill-alpha"
    skill_a_dir.mkdir(parents=True)
    (skill_a_dir / "SKILL.md").write_text(
        "---\nname: skill-alpha\n"
        "description: Alpha skill for testing dashboard rendering\n---\n# Alpha\n",
        encoding="utf-8",
    )

    # Skill B: low effectiveness, few executions, trending down
    skill_b_dir = claude_skills_dir / "skill-beta"
    skill_b_dir.mkdir(parents=True)
    (skill_b_dir / "SKILL.md").write_text(
        "---\nname: skill-beta\n"
        "description: Beta skill with low effectiveness\n---\n# Beta\n",
        encoding="utf-8",
    )

    # Skill C: no DB match, has events only
    skill_c_dir = claude_skills_dir / "skill-gamma"
    skill_c_dir.mkdir(parents=True)
    (skill_c_dir / "SKILL.md").write_text(
        "---\nname: skill-gamma\n"
        "description: Gamma skill with events but no DB entry\n---\n# Gamma\n",
        encoding="utf-8",
    )

    # Skill D: exact id match (test-skill-001 from JSON above)
    skill_d_dir = claude_skills_dir / "test-skill-001"
    skill_d_dir.mkdir(parents=True)
    (skill_d_dir / "SKILL.md").write_text(
        "---\nname: test-skill-001\n"
        "description: A test skill for dashboard testing\n---\n# Test\n",
        encoding="utf-8",
    )

    # --- Create skills.db ---
    skills_db_path = tmp_path / "memory" / "skills.db"
    sconn = sqlite3.connect(str(skills_db_path))
    sconn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
            description TEXT NOT NULL, execution_pattern TEXT NOT NULL,
            average_effectiveness REAL NOT NULL, total_executions INTEGER NOT NULL,
            successful_executions INTEGER NOT NULL, last_used_at TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            version INTEGER NOT NULL, file_path TEXT NOT NULL, embedding TEXT,
            claude_skill_name TEXT
        )
    """)
    sconn.execute("""
        CREATE TABLE IF NOT EXISTS skill_usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, context TEXT NOT NULL,
            skill_id TEXT, effectiveness REAL, timestamp TEXT NOT NULL
        )
    """)
    sconn.execute("""
        CREATE TABLE IF NOT EXISTS skill_session_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_date TEXT NOT NULL,
            skill_name TEXT NOT NULL, event_type TEXT NOT NULL,
            description TEXT NOT NULL, step_ref TEXT, timestamp TEXT NOT NULL
        )
    """)

    # DB skill matching test-skill-001 (exact id match)
    sconn.execute(
        "INSERT INTO skills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "test-skill-001", "Test Skill", "conversation-skills",
            "A test skill for dashboard testing",
            "When testing dashboard, verify all pages render",
            0.75, 10, 8, "2026-03-20T10:00:00",
            "2026-03-10T00:00:00", "2026-03-20T10:00:00", 2,
            str(skills_dir / "conversation-skills" / "test-skill-001.json"), None,
            "test-skill-001",  # claude_skill_name = exact id
        ),
    )

    # DB skill matching skill-alpha (via claude_skill_name)
    sconn.execute(
        "INSERT INTO skills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "skill_hash_alpha", "Alpha Skill", "automation-skills",
            "Alpha skill: for testing dashboard rendering",
            "alpha trigger",
            0.92, 25, 23, "2026-03-25T10:00:00",
            "2026-03-01T00:00:00", "2026-03-25T10:00:00", 3,
            "path/alpha.json", None,
            "skill-alpha",  # claude_skill_name
        ),
    )

    # DB skill matching skill-beta (via claude_skill_name)
    sconn.execute(
        "INSERT INTO skills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "skill_hash_beta", "Beta Skill", "meta-skills",
            "Beta skill: with low effectiveness",
            "beta trigger",
            0.35, 5, 2, "2026-03-18T10:00:00",
            "2026-03-05T00:00:00", "2026-03-18T10:00:00", 1,
            "path/beta.json", None,
            "skill-beta",  # claude_skill_name
        ),
    )

    # Usage log for test-skill-001 (trend: up)
    for i, eff in enumerate([0.6, 0.65, 0.7, 0.75, 0.8]):
        sconn.execute(
            "INSERT INTO skill_usage_log (context, skill_id, effectiveness, timestamp) VALUES (?,?,?,?)",
            (f"test context {i}", "test-skill-001", eff, f"2026-03-{15+i}T10:00:00"),
        )

    # Usage log for alpha (trend: up)
    for i, eff in enumerate([0.80, 0.84, 0.88, 0.90, 0.92]):
        sconn.execute(
            "INSERT INTO skill_usage_log (context, skill_id, effectiveness, timestamp) VALUES (?,?,?,?)",
            (f"alpha context {i}", "skill_hash_alpha", eff, f"2026-03-{20+i}T10:00:00"),
        )

    # Usage log for beta (trend: down)
    for i, eff in enumerate([0.50, 0.45, 0.40, 0.38, 0.35]):
        sconn.execute(
            "INSERT INTO skill_usage_log (context, skill_id, effectiveness, timestamp) VALUES (?,?,?,?)",
            (f"beta context {i}", "skill_hash_beta", eff, f"2026-03-{10+i}T10:00:00"),
        )

    # Session events for test-skill-001 (skill_name matches DB skill name for detail view)
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (1, "2026-03-20", "Test Skill", "skill_start", "Started test", None, "2026-03-20T10:00:00"),
    )
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (2, "2026-03-20", "Test Skill", "extra_step", "Added validation", "Step 3", "2026-03-20T10:05:00"),
    )
    # Also register under the directory name for event stats matching
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (6, "2026-03-20", "test-skill-001", "skill_start", "Started test", None, "2026-03-20T10:00:00"),
    )
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (7, "2026-03-20", "test-skill-001", "extra_step", "Added validation", "Step 3", "2026-03-20T10:05:00"),
    )

    # Session events for skill-gamma (events but no DB skill)
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (3, "2026-03-22", "skill-gamma", "skill_start", "Started gamma", None, "2026-03-22T09:00:00"),
    )
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (4, "2026-03-22", "skill-gamma", "user_correction", "Wrong output", None, "2026-03-22T09:10:00"),
    )
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (5, "2026-03-22", "skill-gamma", "skill_end", "Completed gamma", None, "2026-03-22T09:15:00"),
    )

    sconn.commit()
    sconn.close()

    # Register test .claude/skills/ dir for scanning
    from cognitive_memory.dashboard.services import skills_service
    skills_service._CLAUDE_SKILLS_DIRS.append(claude_skills_dir)

    yield tmp_path

    # Cleanup: remove added path
    if claude_skills_dir in skills_service._CLAUDE_SKILLS_DIRS:
        skills_service._CLAUDE_SKILLS_DIRS.remove(claude_skills_dir)


def _setup_knowledge_files(tmp_path, error_patterns_content, summary_content):
    """Helper to create knowledge directory and files."""
    knowledge_dir = tmp_path / "memory" / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "error-patterns.md").write_text(
        error_patterns_content, encoding="utf-8"
    )
    (knowledge_dir / "summary.md").write_text(
        summary_content, encoding="utf-8"
    )


@pytest.fixture
def crystal_rich_dir(tmp_path):
    """Crystallization-rich project: multiple signals triggered, 3 error patterns, 3 principles.

    Signals:
      - PATTERN count = 3 (>= threshold 3) → TRIGGERED
      - ERROR count = 5 (>= threshold 5) → TRIGGERED
      - log_days = 3 (< threshold 10)
      - days_since_checkpoint = 0 (< threshold 21)
    """
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)

    (logs_dir / "2026-03-18.md").write_text(SAMPLE_LOG_PATTERNS, encoding="utf-8")
    (logs_dir / "2026-03-19.md").write_text(SAMPLE_LOG_MORE_ERRORS, encoding="utf-8")
    (logs_dir / "2026-03-20.md").write_text(SAMPLE_LOG, encoding="utf-8")

    _setup_knowledge_files(tmp_path, SAMPLE_ERROR_PATTERNS, SAMPLE_KNOWLEDGE_SUMMARY)

    (tmp_path / "cogmem.toml").write_text(
        COGMEM_TOML_WITH_CRYSTALLIZATION, encoding="utf-8"
    )

    # Minimal vectors.db (signals uses filesystem, not DB)
    db_path = tmp_path / "memory" / "vectors.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY, content_hash TEXT UNIQUE,
        date TEXT, content TEXT, arousal REAL, vector BLOB
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS indexed_files (
        filename TEXT PRIMARY KEY, indexed_at TEXT, entry_count INTEGER
    )""")
    conn.commit()
    conn.close()

    yield tmp_path


@pytest.fixture
def crystal_empty_dir(tmp_path):
    """Empty crystallization project: no signals, no error patterns, no principles.

    Signals:
      - PATTERN count = 0
      - ERROR count = 0
      - log_days = 0
      - days_since_checkpoint = 9999 (never checkpointed) → TRIGGERED
    """
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)

    _setup_knowledge_files(
        tmp_path, SAMPLE_ERROR_PATTERNS_EMPTY, SAMPLE_KNOWLEDGE_SUMMARY_EMPTY
    )

    (tmp_path / "cogmem.toml").write_text(
        COGMEM_TOML_NEVER_CRYSTALLIZED, encoding="utf-8"
    )

    db_path = tmp_path / "memory" / "vectors.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY, content_hash TEXT UNIQUE,
        date TEXT, content TEXT, arousal REAL, vector BLOB
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS indexed_files (
        filename TEXT PRIMARY KEY, indexed_at TEXT, entry_count INTEGER
    )""")
    conn.commit()
    conn.close()

    yield tmp_path


@pytest.fixture
def crystal_boundary_dir(tmp_path):
    """Boundary test: counts just below thresholds (PATTERN=2, ERROR=4, log_days=2).

    Signals:
      - PATTERN count = 2 (< threshold 3)
      - ERROR count = 4 (< threshold 5)
      - log_days = 2 (< threshold 10)
      - days_since_checkpoint = 1 (< threshold 21)
    All conditions NOT triggered.
    """
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)

    # 2 PATTERNs, 4 ERRORs across 2 log files
    boundary_log_a = """\
# 2026-03-24 セッションログ

## セッション概要
境界値テスト用セッション A。

## ログエントリ

### [PATTERN] パターン1
*Arousal: 0.7 | Emotion: Self-awareness*
1つ目のパターン。

---

### [PATTERN] パターン2
*Arousal: 0.7 | Emotion: Self-awareness*
2つ目のパターン。

---

### [ERROR] エラー1
*Arousal: 0.8 | Emotion: Correction*
1つ目のエラー。

---

### [ERROR] エラー2
*Arousal: 0.8 | Emotion: Correction*
2つ目のエラー。

---

## 引き継ぎ
- **次のアクション**: テスト
"""
    boundary_log_b = """\
# 2026-03-25 セッションログ

## セッション概要
境界値テスト用セッション B。

## ログエントリ

### [ERROR] エラー3
*Arousal: 0.7 | Emotion: Correction*
3つ目のエラー。

---

### [ERROR] エラー4
*Arousal: 0.6 | Emotion: Correction*
4つ目のエラー。

---

### [INSIGHT] 洞察
*Arousal: 0.8 | Emotion: Discovery*
テスト用の洞察。

---

## 引き継ぎ
- **次のアクション**: 境界値確認
"""

    (logs_dir / "2026-03-24.md").write_text(boundary_log_a, encoding="utf-8")
    (logs_dir / "2026-03-25.md").write_text(boundary_log_b, encoding="utf-8")

    # 1 error pattern only
    single_ep = """\
# エラーパターン

*最終更新: 2026-03-25*

---

## EP-001: 浅い探索で存在するリソースを見落とす
**発生**: 2026-03-25 | **Arousal**: 0.8
**パターン**: ディレクトリの一部だけ見て判断する。
**対策**: 網羅的に探索する。
"""

    # 1 principle only
    single_principle = """\
# 知識サマリー

*最終更新: 2026-03-25*

---

## 確立された判断原則

### 1. 探索は網羅的に、検証は実データで
浅い探索で早合点しない。

## エラーパターン
→ 詳細は `error-patterns.md` 参照（EP-001）

## アクティブプロジェクト
[なし]
"""

    _setup_knowledge_files(tmp_path, single_ep, single_principle)

    (tmp_path / "cogmem.toml").write_text(
        COGMEM_TOML_BOUNDARY, encoding="utf-8"
    )

    db_path = tmp_path / "memory" / "vectors.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY, content_hash TEXT UNIQUE,
        date TEXT, content TEXT, arousal REAL, vector BLOB
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS indexed_files (
        filename TEXT PRIMARY KEY, indexed_at TEXT, entry_count INTEGER
    )""")
    conn.commit()
    conn.close()

    yield tmp_path


@pytest.fixture
def crystal_rich_config(crystal_rich_dir):
    return CogMemConfig.from_toml(crystal_rich_dir / "cogmem.toml")


@pytest.fixture
def crystal_empty_config(crystal_empty_dir):
    return CogMemConfig.from_toml(crystal_empty_dir / "cogmem.toml")


@pytest.fixture
def crystal_boundary_config(crystal_boundary_dir):
    return CogMemConfig.from_toml(crystal_boundary_dir / "cogmem.toml")


@pytest.fixture
def crystal_rich_client(crystal_rich_config):
    from starlette.testclient import TestClient
    return TestClient(create_app(crystal_rich_config))


@pytest.fixture
def crystal_empty_client(crystal_empty_config):
    from starlette.testclient import TestClient
    return TestClient(create_app(crystal_empty_config))


@pytest.fixture
def crystal_boundary_client(crystal_boundary_config):
    from starlette.testclient import TestClient
    return TestClient(create_app(crystal_boundary_config))


@pytest.fixture
def config(project_dir):
    """Load config from the test project directory."""
    return CogMemConfig.from_toml(project_dir / "cogmem.toml")


@pytest.fixture
def app(config):
    """Create a FastAPI test app."""
    return create_app(config)


@pytest.fixture
def client(app):
    """Create a synchronous test client."""
    from starlette.testclient import TestClient
    return TestClient(app)
