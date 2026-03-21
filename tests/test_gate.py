"""Tests for gate module: should_search adaptive gate."""

import pytest

from cognitive_memory.gate import should_search


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
        assert should_search("検索") is False


class TestASCIIThreshold:
    def test_ascii_above_threshold(self):
        assert should_search("semantic search design") is True

    def test_ascii_below_threshold(self):
        assert should_search("search") is False


class TestEdgeCases:
    def test_empty_query(self):
        assert should_search("") is False
        assert should_search("   ") is False

    def test_force_overrides_skip(self):
        # "以前" (force) in a greeting-like context
        assert should_search("以前おはようって言った") is True
