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


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal cogmem project with sample data."""
    logs_dir = tmp_path / "memory" / "logs"
    logs_dir.mkdir(parents=True)

    # Write sample log
    (logs_dir / "2026-03-20.md").write_text(SAMPLE_LOG, encoding="utf-8")

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

    # Create skills.db with matching data
    skills_db_path = tmp_path / "memory" / "skills.db"
    sconn = sqlite3.connect(str(skills_db_path))
    sconn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
            description TEXT NOT NULL, execution_pattern TEXT NOT NULL,
            average_effectiveness REAL NOT NULL, total_executions INTEGER NOT NULL,
            successful_executions INTEGER NOT NULL, last_used_at TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            version INTEGER NOT NULL, file_path TEXT NOT NULL, embedding TEXT
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
    sconn.execute(
        "INSERT INTO skills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "test-skill-001", "Test Skill", "conversation-skills",
            "A test skill for dashboard testing",
            "When testing dashboard, verify all pages render",
            0.75, 10, 8, "2026-03-20T10:00:00",
            "2026-03-10T00:00:00", "2026-03-20T10:00:00", 2,
            str(skills_dir / "conversation-skills" / "test-skill-001.json"), None,
        ),
    )
    # Insert usage log entries for trend testing
    for i, eff in enumerate([0.6, 0.65, 0.7, 0.75, 0.8]):
        sconn.execute(
            "INSERT INTO skill_usage_log (context, skill_id, effectiveness, timestamp) VALUES (?,?,?,?)",
            (f"test context {i}", "test-skill-001", eff, f"2026-03-{15+i}T10:00:00"),
        )
    # Insert session events
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (1, "2026-03-20", "Test Skill", "skill_start", "Started test", None, "2026-03-20T10:00:00"),
    )
    sconn.execute(
        "INSERT INTO skill_session_events VALUES (?,?,?,?,?,?,?)",
        (2, "2026-03-20", "Test Skill", "extra_step", "Added validation", "Step 3", "2026-03-20T10:05:00"),
    )
    sconn.commit()
    sconn.close()

    return tmp_path


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
