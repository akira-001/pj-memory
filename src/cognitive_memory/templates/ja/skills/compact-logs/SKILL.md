---
name: compact-logs
description: memory/logs/ 配下の生ログから重要エントリのみ抽出して .compact.md を生成し Session Init の読み込みコストを削減する。Claude Code ネイティブの会話履歴圧縮 /compact とは別物。「ログ圧縮」「memory/logs 圧縮」「日次ログを圧縮」で起動。
user-invocable: true
---

# SKILL: /compact-logs — ログ圧縮

**トリガー**: `/compact-logs` または 自動（ログファイルが10日分を超えた時）
**所要時間**: 5〜10分
**目的**: 生ログから重要エントリのみを抽出し、Session Init の読み込みコストを削減する

> 注意: このスキルはディスク上の memory/logs/ ファイルを圧縮するものです。
> Claude Code ネイティブの `/compact`（会話履歴の圧縮）とは異なります。

---

## 実行手順

### Step 1: 対象ファイルの確認

```
Glob: memory/logs/*.md（.compact.md を除く）
```

`.compact.md` が存在しないファイルのみが圧縮対象。
すでに `.compact.md` があるファイルはスキップ（再圧縮は `/compact-logs --force` で）。

### Step 2: 重要エントリのフィルタリング

**保持するエントリ（以下のいずれかを満たすもの）**:
- Arousal >= 0.6 のエントリ
- カテゴリが `[INSIGHT]` / `[DECISION]` / `[MILESTONE]` のもの
- 引き継ぎセクションに記載されたもの

**省略するエントリ**:
- Arousal < 0.4 の `[QUESTION]`（解決済みの軽い問い）
- 同一テーマの `[PATTERN]` エントリ（初回のみ保持、以降は件数カウントのみ）
- `[ERROR]` のうちすでに `[DECISION]` で解決済みのもの

### Step 3: .compact.md を生成

```
Write: memory/logs/YYYY-MM-DD.compact.md
```

フォーマット:

```markdown
# YYYY-MM-DD コンパクトログ
*元ログ: YYYY-MM-DD.md | 圧縮率: N% | 生成: YYYY-MM-DD*

## エッセンス
[セッション概要の1行サマリー]

## 重要エントリ（Arousal >= 0.6）
[フィルタ済みエントリ群]

## 引き継ぎ
[元ログの引き継ぎセクション]
```

### Step 4: 完了報告

```
## /compact-logs 完了

**処理ファイル**: N件
**圧縮率**: 平均 X%（エントリ数: M → K）
**Session Init**: 次回から .compact.md を優先読み込みします
```

---

## Session Init との連携

Session Init Step 2（直近ログ読み込み）で:
1. `.compact.md` が存在する → `.compact.md` を読み込む（優先）
2. `.compact.md` が存在しない → 通常の `.md` を読み込む

生ログ（`.md`）は削除しない。`/search` の検索対象として常に保持する。

---

## 自動トリガー条件

Session Init（結晶化シグナル）と同じタイミングでチェック:

```
log_file_count >= 10  # ログファイルが10日分以上
```

条件を満たす場合、Session Init の応答冒頭に通知を追加:

```
💡 /compact-logs 推奨: ログが10日分を超えました。/compact-logs を実行しますか？
```

---

## オプション

| コマンド | 動作 |
|---------|------|
| `/compact-logs` | 未圧縮ファイルのみ処理 |
| `/compact-logs --force` | 全ファイルを再圧縮 |
| `/compact-logs --preview` | 実際に書き込まず、圧縮結果をプレビュー |
