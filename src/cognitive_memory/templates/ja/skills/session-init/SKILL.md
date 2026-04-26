---
name: session-init
description: セッション開始時に実行。contexts/ ブリーフィング優先読み込み・cogmem index/signals を実行し、フラッシュバック・シグナルを通知する
user-invocable: false
---

# SKILL: Session Init

**トリガー**: 会話開始（挨拶、「はじめよう」、新しいトピック）
**目的**: 前回セッションの文脈を復元し、記憶・シグナルを確認する

> identity/soul.md、knowledge/summary.md は @参照で既にコンテキストにあるため Read しない。
> identity/user.md は共有テンプレート。per-user プロファイルは Step 0 で読み込む。

---

## Step 0: Per-user プロファイル読み込み

`cogmem.local.toml` から `user_id` を取得し、per-user プロファイルを読み込む:

```bash
# user_id を取得（cogmem.local.toml → cogmem.toml の順で探す）
grep -m1 'user_id' cogmem.local.toml 2>/dev/null || grep -m1 'user_id' cogmem.toml 2>/dev/null
```

- `user_id` が見つかった場合 → `identity/users/{user_id}.md` を Read
- ファイルが存在しない場合 → スキップ（@identity/user.md がフォールバック）
- `user_id` が空 / 未設定 → スキップ

## Step 1: 最新 contexts ブリーフィングを確認

```bash
ls -t memory/contexts/*.md | grep -v .gitkeep | head -1
```

- **ファイルが存在し、2日以内**のもの → Read してコンテキスト復元 → Step 2 をスキップ
- **存在しない / 古い** → Step 2 へ（フォールバック）

## Step 2: 引き継ぎセクションのみ Read（フォールバック）

*Step 1 で contexts ファイルが取得できた場合はスキップ*

```bash
ls -t memory/logs/*.md | head -2
```

最新ログ1ファイルのみ対象（`.compact.md` 優先）。
ファイル全体ではなく「## 引き継ぎ」セクション付近（末尾 40 行）のみ Read する:
```
Read: <ファイルパス>  offset=-40行分
```

**【遅延ラップ検知】** 「## 引き継ぎ」セクションが空または存在しない場合（= wrap 未実行）:
1. ログ全体を Read してセッション概要（1〜2行）を生成
2. 「## セッション概要」を記入
3. 「## 引き継ぎ」を生成・記入
4. `memory/contexts/YYYY-MM-DD.md` を生成（wrap スキルの Step 2.5 と同様）
※ 本日分のログは対象外（現セッション中のため）

## Step 3: cogmem index を実行

```bash
cogmem index
```
- Ollama 未起動時はスキップ
- cogmem 未インストール時は `pip install cogmem-agent` を実行

## Step 4: 並列実行（Step 3 完了後）

以下の2つを**並列**で実行する:

```bash
# 1. 記憶の定着シグナルチェック
cogmem signals

# 2. キーワード検索（会話に具体的なトピックがある場合のみ）
cogmem search "<現在の会話コンテキストのキーワード>"
```

**cogmem search の実行条件**: 会話に「再開」「こんにちは」のような汎用フレーズしかない場合はスキップ。具体的なプロジェクト名・技術名・タスク名が含まれる場合のみ実行。

### フラッシュバック判定
- `score >= 0.75` かつ `arousal >= 0.6` のエントリ → フラッシュバックとして提示
- 覚えている体で自然に伝える（日付・スコアの機械的報告はしない）:
  「前に [内容] について話したよね。今の話題と繋がりそう」
- 忘却済みログでも、文脈類似度と Arousal が高ければ復活させる

### signals 判定
- 条件を満たす場合のみ通知（Wrap まで待つ、Init では実行しない）

> **Note**: `cogmem skills audit` は Init では実行しない。Wrap の Step 3 に移動済み。

## Step 5: トークン予算チェック

目標: 合計 6k tokens。超過時は `/compact` を推奨。

## Step 6: アップグレード確認（24hキャッシュ、fail-open）

セッション毎に1回呼び出すが、`cogmem.toml [updates]` で24hサーバーサイドキャッシュ:

```bash
cogmem upgrade-check --json
```

結果スキーマ:
```json
{
  "status": "up_to_date" | "upgrade_available" | "skipped" | "error",
  "current": "0.25.0",
  "latest": "0.26.0",
  "release_date": "2026-04-26",
  "upgrade_command": "pip install -U cogmem-agent",
  "post_install": "cogmem init",
  "skill_template_updates": 3
}
```

`status` 別の挙動:
- `up_to_date` / `skipped` / `error` → 通知しない（**ただし** `skill_template_updates > 0` の場合は別途通知）
- `upgrade_available` → 必ず応答に通知を追加（応答フォーマット参照）

独立した2シグナル、片方だけ・両方どちらも通知:

**シグナル1: パッケージアップデート** (`upgrade_available`):
- **y** → `pip install -U cogmem-agent && cogmem init --update-skills` 実行
- **n** → `cogmem upgrade-check --snooze-days 7`（7日スヌーズ）
- **later** → 何もしない、次回 24h キャッシュ切れで再表示

**シグナル2: skill テンプレート差分** (`skill_template_updates > 0`):
パッケージは同じバージョンでも、同梱 skill テンプレートが進化している場合がある
（trigger 追加など）。次のように通知:
- **y** → `cogmem skills update-templates`（対話的 per-skill 確認 + 自動バックアップ）
- **n** → 今セッションは抑制

自動アップグレードはしない。`[updates].auto = "never"` を尊重（CLI が処理して `skipped` を返す）。

---

## 応答フォーマット

通知がある場合のみ冒頭に追加:

```
⚠️ 記憶の定着シグナル検知: [条件内容]（該当時のみ）
💭 フラッシュバック: [過去エントリの抜粋]（該当時のみ）
📊 トークン予算超過: [推奨アクション]（超過時のみ）
📦 アップデートあり: cogmem-agent X.Y.Z（現在: A.B.C）。アップグレードしますか？ (y/n/later)
📝 N 件の skill にテンプレート更新があります。`cogmem skills update-templates` を実行しますか？ (y/n)
---
[通常の応答]
```
