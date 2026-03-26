"""Internationalization for cogmem dashboard."""

from __future__ import annotations

from typing import Any

TRANSLATIONS: dict[str, dict[str, str]] = {
    # Navigation
    "nav.memory": {"en": "Memory Overview", "ja": "メモリー概要"},
    "nav.skills": {"en": "Skills", "ja": "スキル"},
    "nav.logs": {"en": "Logs", "ja": "ログ"},
    "nav.search": {"en": "Search", "ja": "検索"},
    "nav.personality": {"en": "Personality", "ja": "パーソナリティ"},
    "nav.crystallization": {"en": "Memory Consolidation", "ja": "記憶の定着"},

    # Memory Overview
    "memory.title": {"en": "Memory Overview", "ja": "メモリー概要"},
    "memory.subtitle": {"en": "Aggregate view of all stored memories", "ja": "蓄積された記憶の全体像"},
    "memory.total_memories": {"en": "Total Memories", "ja": "総メモリー数"},
    "memory.since": {"en": "Since", "ja": "開始日"},
    "memory.date_range": {"en": "Date Range", "ja": "期間"},
    "memory.no_data": {"en": "No data", "ja": "データなし"},
    "memory.avg_arousal": {"en": "Avg Arousal", "ja": "平均アルーサル"},
    "memory.scale": {"en": "Scale 0.0 – 1.0", "ja": "スケール 0.0 – 1.0"},
    "memory.categories": {"en": "Categories", "ja": "カテゴリ"},
    "memory.daily_accumulation": {"en": "Daily Accumulation", "ja": "日別蓄積"},
    "memory.daily_desc": {"en": "Number of memory entries recorded per day", "ja": "日別の記憶エントリ数"},
    "memory.category_breakdown": {"en": "Category Breakdown", "ja": "カテゴリ内訳"},
    "memory.category_desc": {"en": "Distribution of entries by category tag", "ja": "カテゴリタグ別のエントリ分布"},
    "memory.arousal_distribution": {"en": "Arousal Distribution", "ja": "アルーサル分布"},
    "memory.arousal_desc": {"en": "Distribution of emotional intensity scores (0.4-1.0)", "ja": "情動強度スコアの分布 (0.4-1.0)"},
    "memory.crystallization": {"en": "Memory Consolidation Signals", "ja": "記憶の定着シグナル"},
    "memory.crystal_desc": {"en": "Conditions for triggering memory consolidation", "ja": "記憶の定着トリガー条件"},
    "memory.crystal_recommended": {"en": "Memory consolidation recommended", "ja": "記憶の定着を推奨"},
    "memory.conditions_met": {"en": "condition(s) met", "ja": "個の条件が成立"},
    "memory.pattern_entries": {"en": "Pattern entries", "ja": "パターンエントリ"},
    "memory.error_entries": {"en": "Error entries", "ja": "エラーエントリ"},
    "memory.log_days": {"en": "Log days", "ja": "ログ日数"},
    "memory.days_since_cp": {"en": "Days since checkpoint", "ja": "チェックポイントからの日数"},
    "memory.days": {"en": "days", "ja": "日間"},
    "memory.memories": {"en": "Memories", "ja": "メモリー"},
    "memory.most_recalled": {"en": "Most Recalled Memories", "ja": "よく想起される記憶"},
    "memory.recall_count": {"en": "Recalls", "ja": "想起回数"},
    "memory.last_recalled": {"en": "Last Recalled", "ja": "最終想起"},
    "memory.no_recalls": {"en": "No recalled memories yet.", "ja": "想起された記憶はまだありません。"},

    # Skills
    "skills.title": {"en": "Skills", "ja": "スキル"},
    "skills.subtitle": {"en": "Monitor skill effectiveness and improvement status", "ja": "スキルの改善状況を確認"},
    "skills.audit_summary": {"en": "Audit Summary", "ja": "監査サマリー"},
    "skills.total": {"en": "Total", "ja": "合計"},
    "skills.needs_improvement": {"en": "Needs Improvement", "ja": "改善が必要"},
    "skills.suggested_new": {"en": "Suggested New", "ja": "新規提案"},
    "skills.stale": {"en": "Stale", "ja": "未使用"},
    "skills.name": {"en": "Name", "ja": "名前"},
    "skills.category": {"en": "Category", "ja": "カテゴリ"},
    "skills.effectiveness": {"en": "Effectiveness", "ja": "有効性"},
    "skills.executions": {"en": "Executions", "ja": "実行回数"},
    "skills.last_used": {"en": "Last Used", "ja": "最終使用"},
    "skills.trend": {"en": "Trend", "ja": "トレンド"},
    "skills.no_skills": {"en": "No skills registered yet.", "ja": "スキルが登録されていません。"},
    "skills.recommendations": {"en": "Recommendations", "ja": "推奨アクション"},
    "skills.no_recommendations": {"en": "No recommendations at this time.", "ja": "現在推奨事項はありません。"},
    "skills.overview": {"en": "Overview", "ja": "概要"},
    "skills.description": {"en": "Description", "ja": "説明"},
    "skills.exec_pattern": {"en": "Execution Pattern", "ja": "実行パターン"},
    "skills.version": {"en": "Version", "ja": "バージョン"},
    "skills.created": {"en": "Created", "ja": "作成日"},
    "skills.updated": {"en": "Updated", "ja": "更新日"},
    "skills.eff_trend": {"en": "Effectiveness Trend", "ja": "有効性推移"},
    "skills.events": {"en": "Events", "ja": "イベント"},
    "skills.recent_usage": {"en": "Recent Usage", "ja": "最近の使用"},
    "skills.context": {"en": "Context", "ja": "コンテキスト"},
    "skills.close": {"en": "Close", "ja": "閉じる"},

    # Logs
    "logs.title": {"en": "Session Logs", "ja": "セッションログ"},
    "logs.recent": {"en": "Recent Logs", "ja": "最近のログ"},
    "logs.earlier": {"en": "Earlier", "ja": "それ以前"},
    "logs.entries": {"en": "entries", "ja": "件"},
    "logs.all_logs": {"en": "All Logs", "ja": "全ログ"},
    "logs.session_overview": {"en": "Session Overview", "ja": "セッション概要"},
    "logs.handover": {"en": "Handover", "ja": "引き継ぎ"},
    "logs.all_categories": {"en": "All Categories", "ja": "全カテゴリ"},
    "logs.sort_time": {"en": "Sort: Time", "ja": "ソート: 時系列"},
    "logs.sort_arousal": {"en": "Sort: Arousal", "ja": "ソート: アルーサル"},
    "logs.search_entries": {"en": "Search entries...", "ja": "エントリを検索..."},
    "logs.no_entries": {"en": "No entries match the current filters.", "ja": "条件に一致するエントリがありません。"},
    "logs.no_logs": {"en": "No session logs found.", "ja": "セッションログがありません。"},

    # Search
    "search.title": {"en": "Memory Search", "ja": "メモリー検索"},
    "search.subtitle": {"en": "Search across all indexed memories using semantic similarity", "ja": "セマンティック検索で全メモリーを横断検索"},
    "search.placeholder": {"en": "Search memories...", "ja": "メモリーを検索..."},
    "search.button": {"en": "Search", "ja": "検索"},
    "search.searching": {"en": "Searching...", "ja": "検索中..."},
    "search.results": {"en": "results", "ja": "件"},
    "search.no_results": {"en": "No results found", "ja": "結果が見つかりません"},
    "search.enter_query": {"en": "Enter a query to search your memories", "ja": "検索クエリを入力してください"},
    "search.view_log": {"en": "View log", "ja": "ログを表示"},
    "search.memory_index": {"en": "Memory Index", "ja": "メモリーインデックス"},
    "search.indexed_across": {"en": "memories indexed across", "ja": "件のメモリー（"},
    "search.days_suffix": {"en": "days", "ja": "日間）"},

    # Personality
    "personality.title": {"en": "Personality", "ja": "パーソナリティ"},
    "personality.user_profile": {"en": "User Profile", "ja": "ユーザープロファイル"},
    "personality.agent_identity": {"en": "Agent Identity", "ja": "エージェントのアイデンティティ"},
    "personality.learning_timeline": {"en": "Learning Timeline", "ja": "学習タイムライン"},
    "personality.knowledge_summary": {"en": "Knowledge Summary", "ja": "蓄積された知識"},
    "personality.no_data": {"en": "No data available yet.", "ja": "まだデータがありません。"},
    "personality.no_entries": {"en": "No learning entries yet.", "ja": "学習エントリがまだありません。"},

    # Crystallization
    "crystal.title": {"en": "Memory Consolidation", "ja": "記憶の定着"},
    "crystal.subtitle": {"en": "Knowledge consolidation status and extracted patterns", "ja": "記憶への知識定着状況と抽出パターン"},
    "crystal.signals": {"en": "Consolidation Signals", "ja": "定着シグナル"},
    "crystal.signals_desc": {"en": "When enough patterns, errors, and logs accumulate, it's time to extract knowledge. Each row shows how much has built up versus the threshold for consolidation.", "ja": "パターン・エラー・ログが一定量溜まると、知識を抽出するタイミング。各行は現在の蓄積量と定着に必要な閾値を示している。"},
    "crystal.recommended": {"en": "Consolidation recommended", "ja": "定着を推奨"},
    "crystal.conditions_met": {"en": "condition(s) met", "ja": "個の条件が成立"},
    "crystal.condition": {"en": "Condition", "ja": "条件"},
    "crystal.current": {"en": "Current", "ja": "現在値"},
    "crystal.threshold": {"en": "Threshold", "ja": "閾値"},
    "crystal.status": {"en": "Status", "ja": "状態"},
    "crystal.accumulating": {"en": "Accumulating", "ja": "蓄積中"},
    "crystal.ready": {"en": "Ready", "ja": "十分"},
    "crystal.pattern_entries": {"en": "Pattern entries", "ja": "パターンエントリ"},
    "crystal.error_entries": {"en": "Error entries", "ja": "エラーエントリ"},
    "crystal.log_days": {"en": "Log days", "ja": "ログ日数"},
    "crystal.days_since_cp": {"en": "Days since checkpoint", "ja": "チェックポイントからの日数"},
    "crystal.checkpoint": {"en": "Checkpoint", "ja": "チェックポイント"},
    "crystal.checkpoint_desc": {"en": "Tracks when knowledge was last consolidated and how many times the process has run.", "ja": "最後に知識を定着させた日時と、これまでの実行回数を記録している。"},
    "crystal.last_checkpoint": {"en": "Last Checkpoint", "ja": "最終チェックポイント"},
    "crystal.total_checkpoints": {"en": "Total Checkpoints", "ja": "チェックポイント回数"},
    "crystal.never": {"en": "Never", "ja": "未実施"},
    "crystal.error_patterns": {"en": "Error Patterns", "ja": "エラーパターン"},
    "crystal.error_patterns_desc": {"en": "Recurring mistakes extracted from session logs. Each pattern has a root cause and countermeasure to prevent recurrence.", "ja": "セッションログから抽出された繰り返しのミス。それぞれに原因と再発防止策がある。"},
    "crystal.ep_title": {"en": "Title", "ja": "タイトル"},
    "crystal.ep_date": {"en": "Date", "ja": "発生日"},
    "crystal.no_patterns": {"en": "No error patterns recorded yet.", "ja": "エラーパターンはまだ記録されていません。"},
    "crystal.principles": {"en": "Established Principles", "ja": "確立された判断原則"},
    "crystal.principles_desc": {"en": "Decision-making rules extracted from repeated patterns across sessions. These guide future behavior.", "ja": "複数のセッションで繰り返し確認された意思決定のルール。今後の行動指針として機能する。"},
    "crystal.no_principles": {"en": "No principles established yet.", "ja": "判断原則はまだ確立されていません。"},

    # Common
    "common.loading": {"en": "Loading...", "ja": "読み込み中..."},
    "common.status": {"en": "Status", "ja": "ステータス"},
    "common.arousal": {"en": "arousal", "ja": "アルーサル"},
    "common.for": {"en": "for", "ja": ""},
}


def t(key: str, lang: str = "en") -> str:
    """Get translated text for a key."""
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("en", key))
