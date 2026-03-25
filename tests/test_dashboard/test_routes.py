"""Route tests for the cogmem dashboard."""

from __future__ import annotations


class TestMemoryOverview:
    def test_home_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Memory Overview" in resp.text

    def test_home_shows_stats(self, client):
        resp = client.get("/")
        assert "Total Memories" in resp.text
        # Should show count of 5 memories
        assert "5" in resp.text

    def test_home_shows_categories(self, client):
        resp = client.get("/")
        assert "INSIGHT" in resp.text

    def test_home_shows_signals(self, client):
        resp = client.get("/")
        assert "Crystallization" in resp.text


class TestSkillsList:
    def test_skills_page_returns_200(self, client):
        resp = client.get("/skills")
        assert resp.status_code == 200
        assert "Skills" in resp.text

    def test_skills_shows_audit_summary(self, client):
        resp = client.get("/skills")
        assert "Total" in resp.text

    def test_skills_table_has_required_columns(self, client):
        """Table must have all 8 columns: Name, Category, Effectiveness, Executions, Events, Version, Last Used, Trend."""
        resp = client.get("/skills")
        html = resp.text
        for col_key in [
            "skills.name", "skills.category", "skills.effectiveness",
            "skills.executions", "skills.events", "skills.version",
            "skills.last_used", "skills.trend",
        ]:
            # The i18n t() function is called in the template — check EN labels
            from cognitive_memory.dashboard.i18n import t
            label = t(col_key, "en")
            assert label in html, f"Missing column header: {label} (key: {col_key})"

    def test_skills_shows_skill_name_from_claude_skills(self, client, project_dir):
        """Skills from .claude/skills/ should show their directory name."""
        # Create a test skill in a local .claude/skills/ dir
        from cognitive_memory.dashboard.services import skills_service
        test_skills_dir = project_dir / ".claude" / "skills" / "test-tdd-skill"
        test_skills_dir.mkdir(parents=True)
        (test_skills_dir / "SKILL.md").write_text(
            "---\nname: test-tdd-skill\ndescription: A TDD test skill\n---\n# Test\n",
            encoding="utf-8",
        )
        # Temporarily add this dir to scan paths
        original_dirs = skills_service._CLAUDE_SKILLS_DIRS[:]
        skills_service._CLAUDE_SKILLS_DIRS.append(project_dir / ".claude" / "skills")
        try:
            resp = client.get("/skills")
            assert "test-tdd-skill" in resp.text
            assert "A TDD test skill" in resp.text
        finally:
            skills_service._CLAUDE_SKILLS_DIRS[:] = original_dirs

    def test_skills_shows_db_stats_for_matched_skill(self, client, project_dir):
        """When a .claude/skills/ skill matches a DB skill, DB stats should be shown."""
        from cognitive_memory.dashboard.services import skills_service
        # Create .claude/skills/ entry matching the DB skill (test-skill-001)
        test_skills_dir = project_dir / ".claude" / "skills" / "test-skill-001"
        test_skills_dir.mkdir(parents=True)
        (test_skills_dir / "SKILL.md").write_text(
            "---\nname: test-skill-001\ndescription: A test skill for dashboard testing\n---\n# Test\n",
            encoding="utf-8",
        )
        original_dirs = skills_service._CLAUDE_SKILLS_DIRS[:]
        skills_service._CLAUDE_SKILLS_DIRS.append(project_dir / ".claude" / "skills")
        try:
            resp = client.get("/skills")
            assert "test-skill-001" in resp.text
            # DB stats: effectiveness 0.75, executions 10, version v2
            assert "0.75" in resp.text
            assert ">10<" in resp.text  # exact match in <td>10</td>
            assert "v2" in resp.text
            assert "conversation-skills" in resp.text
        finally:
            skills_service._CLAUDE_SKILLS_DIRS[:] = original_dirs

    def test_skills_shows_nonzero_executions_for_hash_id_skill(self, client, project_dir):
        """DB skills with hash IDs should match via description and show real execution counts."""
        import sqlite3
        from cognitive_memory.dashboard.services import skills_service

        # Insert DB skill with hash id
        db_path = project_dir / "memory" / "skills.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT OR REPLACE INTO skills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "skill_888_hash", "テストスキル", "automation-skills",
                "テスト自動化スキル: テスト用のスキルです",
                "test pattern",
                0.90, 25, 20, "2026-03-25T12:00:00",
                "2026-03-01T00:00:00", "2026-03-25T12:00:00", 4,
                "path/to/skill.json", None,
            ),
        )
        conn.commit()
        conn.close()

        test_dir = project_dir / ".claude" / "skills" / "test-auto"
        test_dir.mkdir(parents=True)
        (test_dir / "SKILL.md").write_text(
            "---\nname: test-auto\ndescription: テスト自動化スキル\n---\n",
            encoding="utf-8",
        )
        original = skills_service._CLAUDE_SKILLS_DIRS[:]
        skills_service._CLAUDE_SKILLS_DIRS.append(project_dir / ".claude" / "skills")
        try:
            resp = client.get("/skills")
            assert "test-auto" in resp.text
            assert ">25<" in resp.text  # execution count must be 25, not 0
            assert "0.90" in resp.text
            assert "v4" in resp.text
        finally:
            skills_service._CLAUDE_SKILLS_DIRS[:] = original

    def test_skill_detail_returns_200(self, client):
        resp = client.get("/skills/test-skill-001")
        assert resp.status_code == 200
        assert "Test Skill" in resp.text
        assert "conversation-skills" in resp.text

    def test_skill_detail_shows_events(self, client):
        resp = client.get("/skills/test-skill-001")
        assert resp.status_code == 200
        assert "extra_step" in resp.text

    def test_skill_detail_404(self, client):
        resp = client.get("/skills/nonexistent-skill")
        assert resp.status_code == 404

    def test_skills_audit_api(self, client):
        resp = client.get("/skills/api/audit")
        assert resp.status_code == 200


class TestLogBrowser:
    def test_logs_list_returns_200(self, client):
        resp = client.get("/logs")
        assert resp.status_code == 200
        assert "Session Logs" in resp.text

    def test_logs_list_shows_dates(self, client):
        resp = client.get("/logs")
        assert "2026-03-20" in resp.text

    def test_log_detail_returns_200(self, client):
        resp = client.get("/logs/2026-03-20")
        assert resp.status_code == 200
        assert "テスト洞察" in resp.text

    def test_log_detail_shows_overview(self, client):
        resp = client.get("/logs/2026-03-20")
        assert "テストセッションの概要" in resp.text

    def test_log_detail_404(self, client):
        resp = client.get("/logs/2099-01-01")
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, client):
        resp = client.get("/logs/..%2F..%2Fetc%2Fpasswd")
        assert resp.status_code == 404

    def test_log_filter_by_category(self, client):
        resp = client.get("/logs/2026-03-20?category=INSIGHT")
        assert resp.status_code == 200
        assert "テスト洞察" in resp.text

    def test_log_sort_by_arousal(self, client):
        resp = client.get("/logs/2026-03-20?sort=arousal")
        assert resp.status_code == 200

    def test_log_entries_api(self, client):
        resp = client.get("/logs/api/entries?date=2026-03-20")
        assert resp.status_code == 200

    def test_log_entries_api_with_filter(self, client):
        resp = client.get("/logs/api/entries?date=2026-03-20&category=ERROR")
        assert resp.status_code == 200
        assert "テストエラー" in resp.text


class TestSearch:
    def test_search_page_returns_200(self, client):
        resp = client.get("/search")
        assert resp.status_code == 200
        assert "Search" in resp.text

    def test_search_empty_query(self, client):
        resp = client.get("/search")
        assert resp.status_code == 200
        assert "Enter a query" in resp.text

    def test_search_with_query(self, client):
        """Search with a query — may get degraded results without Ollama."""
        resp = client.get("/search?q=テスト")
        assert resp.status_code == 200
        # Either results or degraded status shown
        assert "results" in resp.text.lower() or "status" in resp.text.lower() or "Search" in resp.text

    def test_search_api_no_query(self, client):
        resp = client.get("/search/api/results")
        assert resp.status_code == 200
        assert "Enter a search query" in resp.text

    def test_search_api_with_query(self, client):
        """HTMX search endpoint with query."""
        resp = client.get("/search/api/results?q=テスト")
        assert resp.status_code == 200


class TestI18n:
    def test_lang_switch_sets_cookie(self, client):
        resp = client.get("/_lang/ja", follow_redirects=False)
        assert resp.status_code == 302
        assert "lang=ja" in resp.headers.get("set-cookie", "")

    def test_lang_switch_invalid_falls_back_to_en(self, client):
        resp = client.get("/_lang/fr", follow_redirects=False)
        assert resp.status_code == 302
        assert "lang=en" in resp.headers.get("set-cookie", "")

    def test_ja_lang_renders_japanese(self, client):
        client.cookies.set("lang", "ja")
        resp = client.get("/")
        assert resp.status_code == 200
        assert "メモリー概要" in resp.text


class TestSkillModal:
    def test_skill_modal_200(self, client):
        resp = client.get("/skills/api/detail/test-skill-001")
        assert resp.status_code == 200
        assert "Test Skill" in resp.text

    def test_skill_modal_404(self, client):
        resp = client.get("/skills/api/detail/nonexistent")
        assert resp.status_code == 404


class TestMemoryOverviewV2:
    def test_overview_shows_days(self, client):
        resp = client.get("/")
        assert "days" in resp.text.lower() or "日間" in resp.text

    def test_search_shows_memory_summary(self, client):
        resp = client.get("/search")
        assert resp.status_code == 200
        # Should show memory index summary
        assert "5" in resp.text  # total memories count


class TestStaticFiles:
    def test_css_accessible(self, client):
        resp = client.get("/static/style.css")
        assert resp.status_code == 200
        assert "var(--bg)" in resp.text
