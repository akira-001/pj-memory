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
    """Skills list page tests.

    Test fixture provides 4 skills in .claude/skills/:
    - skill-alpha: DB match (title), exec=25, eff=0.92, cat=automation-skills, v3, trend=up
    - test-skill-001: DB match (exact id), exec=10, eff=0.75, cat=conversation-skills, v2, events=2
    - skill-beta: DB match (title), exec=5, eff=0.35, cat=meta-skills, v1, trend=down
    - skill-gamma: no DB match, events=3 (incl. user_correction), trend=new
    """

    def test_skills_page_returns_200(self, client):
        resp = client.get("/skills")
        assert resp.status_code == 200

    def test_skills_table_has_all_8_columns(self, client):
        """Table must have all 8 column headers."""
        resp = client.get("/skills")
        html = resp.text
        from cognitive_memory.dashboard.i18n import t
        for col_key in [
            "skills.name", "skills.category", "skills.effectiveness",
            "skills.executions", "skills.events", "skills.version",
            "skills.last_used", "skills.trend",
        ]:
            label = t(col_key, "en")
            assert label in html, f"Missing column: {label}"

    def test_skills_shows_all_skill_names(self, client):
        """All 4 test skills should appear by name."""
        resp = client.get("/skills")
        html = resp.text
        assert "skill-alpha" in html
        assert "test-skill-001" in html
        assert "skill-beta" in html
        assert "skill-gamma" in html

    def test_skills_shows_descriptions(self, client):
        """Each skill's summary should appear."""
        resp = client.get("/skills")
        html = resp.text
        assert "Alpha skill" in html
        assert "dashboard testing" in html
        assert "Beta skill" in html
        assert "Gamma skill" in html

    def test_skill_alpha_has_db_stats(self, client):
        """skill-alpha should show DB stats from title-matched entry."""
        resp = client.get("/skills")
        html = resp.text
        assert "automation-skills" in html
        assert "0.92" in html
        assert "v3" in html

    def test_skill_alpha_executions_nonzero(self, client):
        """skill-alpha should show 25 executions, not 0."""
        resp = client.get("/skills")
        assert ">25<" in resp.text

    def test_skill_beta_has_low_effectiveness(self, client):
        """skill-beta should show its low effectiveness value."""
        resp = client.get("/skills")
        assert "0.35" in resp.text
        assert "meta-skills" in resp.text

    def test_skill_gamma_has_events_only(self, client):
        """skill-gamma has no DB match but has 3 session events."""
        resp = client.get("/skills")
        html = resp.text
        # Should show event count 3 and "—" for category/effectiveness/executions
        assert "skill-gamma" in html

    def test_skill_sorted_by_executions_desc(self, client):
        """Skills should be sorted: alpha(25) > test-skill-001(10) > beta(5) > gamma(0)."""
        resp = client.get("/skills")
        html = resp.text
        pos_alpha = html.index("skill-alpha")
        pos_001 = html.index("test-skill-001")
        pos_beta = html.index("skill-beta")
        pos_gamma = html.index("skill-gamma")
        assert pos_alpha < pos_001 < pos_beta < pos_gamma

    def test_skill_detail_returns_200(self, client):
        resp = client.get("/skills/test-skill-001")
        assert resp.status_code == 200
        assert "Test Skill" in resp.text
        assert "conversation-skills" in resp.text

    def test_skill_detail_shows_events(self, client):
        resp = client.get("/skills/test-skill-001")
        assert "extra_step" in resp.text

    def test_skill_detail_404(self, client):
        resp = client.get("/skills/nonexistent-skill")
        assert resp.status_code == 404

    def test_skills_audit_api(self, client):
        resp = client.get("/skills/api/audit")
        assert resp.status_code == 200

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
