---
name: skill-tracking
description: スキル使用時の追跡・学習プロトコル。skill_start/end/逸脱イベントのログ記録・cogmem track・Skill Feedback・Identity Auto-Update の詳細手順
user-invocable: false
---

# SKILL: Skill Tracking & Feedback

---

## スキル使用開始

スキルの SKILL.md を読んで手順に従い始めた時点でログに記録し、DB にも記録する:

**ログ:**
```
### [SKILL] <skill-name> 使用開始
*Arousal: 0.4 | Emotion: Execution*
[タスクの概要（1行）]

---
```

**DB:**
```bash
cogmem skills track "<skill-name>" --event skill_start --description "<タスクの概要>"
```

## スキル使用完了

```
### [SKILL] <skill-name> 使用完了
*Arousal: 0.4 | Emotion: Completion*
track イベント: N件（extra_step: X, skipped_step: Y, error_recovery: Z, user_correction: W）
→ スムーズに実行 / 改善点あり

---
```

```bash
cogmem skills track "<skill-name>" --event skill_end --description "<結果の概要>"
```

## 逸脱イベント（リアルタイム記録）

手順からの逸脱が発生したら即座に記録する（Live Logging と同じターンで）:

| 発生状況 | event_type |
|---------|------------|
| スキルにない追加手順を実行 | extra_step |
| 手順を意図的にスキップ | skipped_step |
| エラーが発生しリカバリ | error_recovery |
| ユーザーが修正指示を出した | user_correction |

```bash
cogmem skills track "<skill-name>" \
  --event <event_type> \
  --description "<何が起きたかの簡潔な説明>" \
  [--step "<Step N>"]
```

**並列実行ルール:**
- 逸脱イベント（extra_step 等）: メインタスクと並列でバックグラウンド実行可
- skill_start / skill_end: フローの区切りなので同期実行
- cogmem skills learn（タスク完了後）: バックグラウンド実行可

**記録しないケース:** スキル通りにスムーズに実行できた場合（skill_start/end のみ）

---

## Skill Feedback（タスク完了後）

スキルを参照して作業した場合、完了後に実行:

```bash
cd /Users/akira/workspace/open-claude && \
cogmem skills learn --context "<タスクの概要>" --outcome "<結果の概要>" --effectiveness 0.0-1.0
```

### スキルの作成・改善
- `.claude/skills/` に直接作成・編集（YAML frontmatter `description` 必須）
- `superpowers:writing-skills` が利用可能な場合はそのTDDフローに従う

### eval 結果の取り込み
```bash
cd /Users/akira/workspace/open-claude && cogmem skills ingest \
  --benchmark <workspace-path> --skill-name <skill-name>
```

### スキル改善ループ
1. ユーザーに通知し確認を得る
2. `/skill-creator` を起動してスキルを改善
3. eval 完了後に `cogmem skills ingest` で結果を取り込む

### 新スキルの自動生成
同じ種類のタスクを3回以上繰り返した場合、パターンを抽出して新しいスキルを `.claude/skills/` に作成する。

---

## Identity Auto-Update

### identity/user.md — 自動更新（Wrap 時に一括）
ユーザーに関する新しい情報を学んだら Wrap 時に更新:
- セッション中に判明した専門性・スキル
- 観察されたコミュニケーション好み
- 意思決定パターン・思考スタイル
- 基本情報（名前、役割、タイムゾーン）

```bash
cogmem identity update --target user --json '{"セクション名": "内容"}'
```

セッション中にリアルタイムで直接 Edit しても良いが、Wrap Step 4.5 で漏れを補完する。
既存の内容と矛盾する場合は新しい情報で上書きする。

### identity/soul.md — 自動更新
エージェントの振る舞いへのフィードバックがあった場合に更新:
- トーン・話し方の変更リクエスト
- 役割の追加・変更
- コミュニケーションスタイルの変更

```bash
cogmem identity update --target soul --section "セクション名" --content "内容"
```
