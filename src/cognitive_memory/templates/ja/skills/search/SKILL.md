---
name: search
description: Cognitive Memory 横断検索。memory/logs/ を cogmem で横断検索し、過去の類似エントリを発見・提示する。「過去ログ見て」「過去ログから探して」「ログから探して」「以前の話したっけ」「前にやった」「以前の検証」「前回の議論」「過去の決定」など、過去の記録を意識的に探す場面で使う。Session Init の自動フラッシュバック検知でも起動。
user-invocable: true
---

# SKILL: /search — Cognitive Memory 横断検索

**トリガー**: `/search [キーワード]` または Session Init の自動フラッシュバック検知
**所要時間**: 30秒〜1分
**目的**: memory/logs/ を横断検索し、過去の類似エントリを発見・提示する

---

## 実行手順

### Step 1: 検索クエリの解析

- `/search [キーワード]` の場合: キーワードをそのまま使用
- Session Init 自動呼出しの場合: 現在の会話コンテキストから 3〜5 キーワードを抽出

### Step 2: セマンティック検索の実行

```bash
cogmem search "[キーワード]" --json
```

このコマンドが以下を自動で処理する:
1. **適応ゲート**: 挨拶・短文・スラッシュコマンドは検索スキップ
2. **セマンティック検索**: Ollama (multilingual-e5-large) + SQLite でコサイン類似度検索
3. **キーワード検索**: Python 内蔵の Grep 相当
4. **マージ・重複除去**: セマンティック優先、content ベースで重複除去
5. **スコアリング**: `(0.7 * cosine_sim + 0.3 * arousal) * time_decay`
6. **failOpen**: Ollama 障害時は Grep のみで続行

**出力 JSON 形式**:
```json
{
  "results": [
    {"score": 0.78, "date": "2026-03-15", "content": "...", "arousal": 0.8, "source": "semantic"}
  ],
  "status": "ok"
}
```

status の値:
- `"ok"`: 正常（セマンティック + Grep）
- `"degraded (ollama_unavailable)"`: Ollama 障害、Grep のみ
- `"degraded (no_index)"`: インデックス未作成、Grep のみ
- `"skipped_by_gate"`: 適応ゲートでスキップ

### Step 3: フラッシュバック提示

結果の中で score >= 0.75 かつ arousal >= 0.6 のエントリが存在する場合:

```
💭 フラッシュバック: [日付]に「[内容の抜粋]」という話があったよ。今の話と関係ある？
```

### Step 4: 結果をユーザーに提示

ヒット件数と上位3件を表示。0件の場合は「該当なし」と伝えるだけ。

---

## インデックス管理

### インデックス構築

```bash
cogmem index --all    # 全ログを再インデックス
cogmem index          # 差分インデックス（mtime比較）
```

Session Init 時に差分インデックスが自動実行される。

### インデックス統計

```bash
cogmem status
```

### インデックスの場所

`memory/vectors.db`（SQLite、.gitignore 済み）

### インデックス破損時

```bash
rm memory/vectors.db && cogmem index --all
```

Markdown primary は無傷。インデックスは常に再構築可能。

---

## 出力フォーマット

```markdown
## /search 結果: "[キーワード]"

**ヒット**: N件 / 32エントリから検索（status: ok）

| 日付 | カテゴリ | Arousal | Score | 内容（抜粋） |
|------|---------|---------|-------|-------------|
| 2026-03-15 | [INSIGHT] | 0.9 | 0.80 | ... |
| 2026-03-21 | [DECISION] | 0.7 | 0.76 | ... |

💭 フラッシュバック候補: [最も関連度の高いエントリ]
```

---

## `/search` と `context-search` の違い

| | `/search [キーワード]` | `cogmem context-search` |
|--|----------------------|------------------------|
| トリガー | 手動（ユーザーが明示的に呼ぶ） | 自動（Contextual Search Protocol） |
| 結果表示 | フル結果テーブル（上位5件） | フラッシュバック基準通過分のみ（上位3件） |
| フィルタ | なし（全結果を表示） | sim >= 0.65 かつ arousal >= 0.5 |
| 頻度制限 | なし | 1セッション3回まで |
| 用途 | 過去の記録を意識的に探す | 会話中に関連記憶を自動的に浮上させる |

## 自動呼出しのタイミング

- **Session Init**: `/search` スキルで初期フラッシュバック検索
- **会話中（Contextual Search Protocol）**: `cogmem context-search` でトピック変化時に自動検索

## 手動呼出しのシーン

- ユーザーが「以前も同じ話したっけ？」と言った時
- `[PATTERN]` タグが2回目以上のエントリを発見した時
- 新しいテーマを議論し始めた時に過去の文脈を確認したい時
- ユーザーが「過去ログ見て」「ログから探して」「前にやった」「以前の検証は」と言った時
