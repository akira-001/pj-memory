---
name: session-init
description: セッション開始時に実行。コンテキストファイル読み込み・cogmem index/search/signals/audit を並列実行し、フラッシュバック・シグナルを通知する
user-invocable: false
---

# SKILL: Session Init

**トリガー**: 会話開始（挨拶、「はじめよう」、新しいトピック）
**目的**: 前回セッションの文脈を復元し、記憶・シグナルを確認する

> identity/soul.md、identity/user.md、knowledge/summary.md は
> @参照で既にコンテキストにあるため、ここでは Read しない。

---

## Step 1: 本日のコンテキストファイルを確認

```
Read: memory/contexts/YYYY-MM-DD.md（本日の日付）
```
- 存在すれば Read → ユーザーの今日の状態・タスク・気分を把握
- 存在しなければスキップ

## Step 2: 直近ログ2ファイルを Read

```bash
ls -t memory/logs/*.md | head -3
```
- `.compact.md` が存在するファイルは `.compact.md` を優先して Read
- `.compact.md` がなければ通常の `.md` を Read

**【遅延ラップ検知】** Read 後、「## 引き継ぎ」セクションが空または存在しない場合（= wrap 未実行）:
1. ログエントリ全体を走査してセッション概要（1〜2行）を生成
2. 「## セッション概要」を記入
3. 「## 引き継ぎ」を生成・記入
※ 本日分のログは対象外（現セッション中のため）

## Step 3: cogmem index を実行

```bash
cogmem index
```
- Ollama 未起動時はスキップ
- cogmem 未インストール時は `pip install cogmem-agent` を実行

## Step 4-5.5: 並列実行（Step 3 完了後）

以下の3つを**並列**で実行する:

```bash
# 1. キーワード検索（フラッシュバック判定）
cogmem search "<現在の会話コンテキストのキーワード>"

# 2. 記憶の定着シグナルチェック
cogmem signals

# 3. スキル audit
cogmem skills audit --json --brief
```

### フラッシュバック判定
- `score >= 0.75` かつ `arousal >= 0.6` のエントリ → フラッシュバックとして提示
- 覚えている体で自然に伝える（日付・スコアの機械的報告はしない）:
  「前に [内容] について話したよね。今の話題と繋がりそう」
- 忘却済みログでも、文脈類似度と Arousal が高ければ復活させる

### signals 判定
- 条件を満たす場合のみ通知（Wrap まで待つ、Init では実行しない）

### audit 判定
- `recommendations` があれば通知に追加

## Step 6: トークン予算チェック

目標: 合計 6k tokens。超過時は `/compact` を推奨。

---

## 応答フォーマット

通知がある場合のみ冒頭に追加:

```
⚠️ 記憶の定着シグナル検知: [条件内容]（該当時のみ）
💭 フラッシュバック: [過去エントリの抜粋]（該当時のみ）
🔧 Skill audit: [推奨内容]（該当時のみ）
📊 トークン予算超過: [推奨アクション]（超過時のみ）
---
[通常の応答]
```
