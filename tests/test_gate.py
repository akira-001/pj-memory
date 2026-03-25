"""Tests for gate module: should_search adaptive gate."""

import pytest

from cognitive_memory.gate import should_context_search, should_search


class TestForcePatterns:
    def test_force_search_japanese_memory_keywords(self):
        assert should_search("以前こんな話をした") is True
        assert should_search("前回の議論を覚えて") is True
        assert should_search("あの時の決定") is True

    def test_force_search_english_memory_keywords(self):
        assert should_search("remember what we discussed") is True
        assert should_search("previously we decided") is True


class TestSkipPatterns:
    def test_skip_japanese_greetings(self):
        assert should_search("おはよう") is False
        assert should_search("こんにちは") is False
        assert should_search("ありがとう") is False

    def test_skip_slash_commands(self):
        assert should_search("/wrap") is False
        assert should_search("/search test") is False

    def test_skip_english_short_responses(self):
        assert should_search("yes") is False
        assert should_search("ok") is False


class TestCJKThreshold:
    def test_cjk_above_threshold(self):
        assert should_search("セマンティック検索の設計") is True

    def test_cjk_below_threshold(self):
        assert should_search("あ") is False


class TestASCIIThreshold:
    def test_ascii_above_threshold(self):
        assert should_search("semantic search design") is True

    def test_ascii_below_threshold(self):
        assert should_search("abc") is False


class TestEdgeCases:
    def test_empty_query(self):
        assert should_search("") is False
        assert should_search("   ") is False

    def test_force_overrides_skip(self):
        # "以前" (force) in a greeting-like context
        assert should_search("以前おはようって言った") is True


class TestShouldContextSearch:
    def test_delegates_to_should_search(self):
        """If should_search returns True, context search also True."""
        assert should_context_search("以前のセマンティック検索の設計") is True

    def test_topic_patterns_japanese(self):
        """Japanese topic patterns trigger context search."""
        assert should_context_search("データベース設計について") is True

    def test_topic_patterns_english(self):
        """English topic patterns trigger context search."""
        assert should_context_search("what about the caching strategy") is True

    def test_session_keywords_hit(self):
        """session_keywords matching triggers search."""
        assert should_context_search(
            "Proactive Agentの進捗", session_keywords=["Proactive Agent"]
        ) is True

    def test_short_queries_still_skipped(self):
        """Short queries without patterns are skipped."""
        assert should_context_search("はい") is False

    def test_no_match_returns_false(self):
        """Query matching nothing returns False."""
        assert should_context_search("hi") is False

    def test_session_keywords_case_insensitive(self):
        """session_keywords matching is case-insensitive."""
        assert should_context_search(
            "proactive agent stuff", session_keywords=["Proactive Agent"]
        ) is True

    def test_session_keywords_none(self):
        """None session_keywords doesn't crash."""
        assert should_context_search("hi") is False
