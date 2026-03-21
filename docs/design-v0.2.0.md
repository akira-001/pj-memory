# cogmem-agent v0.2.0 設計書

*作成: 2026-03-21 | Eng Review: 2026-03-21 完了 | ステータス: 設計確定・実装待ち*

---

## 概要

cogmem-agent を「記憶検索エンジン」から「Claude Code 向け AIエージェント記憶管理フレームワーク」に拡張する。

`cogmem init` を実行するだけで、任意の Claude Code プロジェクトに認知的記憶体験（Session Init / Live Logging / Wrap / Crystallization / Flashback）が導入される。

---

## アーキテクチャ

### 責務分離

| レイヤー | 担当 | 責務 |
|---------|------|------|
| **ツール層** | cogmem-agent（Python ライブラリ） | ファイル生成、インデックス、検索、シグナル検知 |
| **知能層** | Claude Code（LLM） | Session Init 実行、Live Logging 判断・書込、Wrap 概要生成、Crystallization 実行、フラッシュバック提示、Identity 自動更新 |

ライブラリに LLM 機能は入れない。Claude Code が CLAUDE.md のルールに従って全ての知的処理を実行する。

---

## ディレクトリ構造

`cogmem init` が生成するファイル:

```
project/
  CLAUDE.md                              # Claude Code 用指示書（自動生成）
  cogmem.toml                            # 設定
  memory/
    logs/                                # セッションログ
    contexts/                            # 日次コンテキスト（任意）
    knowledge/
      summary.md                         # 結晶化済み知識サマリー
      error-patterns.md                  # 繰り返すミスパターン
    vectors.db                           # セマンティック検索インデックス（.gitignore）
  identity/
    agent.md                             # エージェントの性格・役割・振る舞い
    user.md                              # ユーザープロファイル（自動更新）
  .gitignore                             # vectors.db 等を除外
```

### 現ワークスペースとの対応表

| 現在（cognitive-memory/） | v0.2.0 | 変更理由 |
|--------------------------|--------|---------|
| `.nfd/identity/SOUL.md` | `identity/agent.md` | NFD用語排除、直感的な命名 |
| `.nfd/identity/USER.md` | `identity/user.md` | 同上 |
| `.nfd/identity/AGENTS.md` | `CLAUDE.md` に統合 | 行動ルールは Claude Code への指示書に直接記述 |
| `memory/MEMORY.md` | `memory/knowledge/summary.md` | 役割を明確に |
| `memory/error-patterns.md` | `memory/knowledge/error-patterns.md` | knowledge/ に集約 |
| `.nfd/config.json` | `cogmem.toml` に統合 | 設定ファイル一本化 |
| `skills/_system/wrap/SKILL.md` | `CLAUDE.md` に統合 | スキルファイル不要 |
| `skills/_system/search/SKILL.md` | `CLAUDE.md` + `cogmem search` | CLI処理 + CLAUDE.mdルール |
| `skills/_system/compact/SKILL.md` | `CLAUDE.md` + `cogmem compact`（将来） | 同上 |
| `skills/_system/crystallize/SKILL.md` | `CLAUDE.md` に統合 | Claude が直接実行 |

---

## 設定ファイル: cogmem.toml

```toml
[cogmem]
logs_dir = "memory/logs"
contexts_dir = "memory/contexts"
db_path = "memory/vectors.db"

[cogmem.identity]
agent = "identity/agent.md"
user = "identity/user.md"

[cogmem.knowledge]
summary = "memory/knowledge/summary.md"
error_patterns = "memory/knowledge/error-patterns.md"

[cogmem.session]
recent_logs = 2                    # Session Init で読む直近ログ数
prefer_compact = true              # .compact.md を優先
token_budget = 6000                # Session Init 合計トークン予算

[cogmem.crystallization]
pattern_threshold = 3              # [PATTERN] N回以上で発火
error_threshold = 5                # [ERROR] 累計N件以上で発火
log_days_threshold = 10            # ログN日分以上で発火
checkpoint_interval_days = 21      # 前回から N日以上で発火
last_checkpoint = ""               # 最終 Checkpoint 日（ISO8601）
checkpoint_count = 0               # 累計 Checkpoint 回数

[cogmem.metrics]
total_sessions = 0                 # 累計セッション数

[cogmem.scoring]
sim_weight = 0.7
arousal_weight = 0.3
base_half_life = 60.0
decay_floor = 0.3

[cogmem.embedding]
provider = "ollama"
model = "zylonai/multilingual-e5-large"
url = "http://localhost:11434/api/embed"
timeout = 10
```

---

## テンプレートファイル

### identity/agent.md

```markdown
# Agent Identity

## Role
[このプロジェクトでのエージェントの役割を記述してください]
例: 開発パートナー、コードレビュアー、企画ブレスト相手

## Communication Style
- 言語: [日本語 / English / etc.]
- トーン: [カジュアル / フォーマル / etc.]
- フォーマット: [箇条書き優先 / 長文OK / etc.]

## Core Values
- [エージェントが重視すべきこと]
例: 根拠を示す、批判的に考える、シンプルさを優先する

## Don'ts
- [エージェントがやってはいけないこと]
例: 根拠なしの楽観、アイデアの即座な全肯定
```

### identity/user.md

```markdown
# User Profile

*このファイルは会話から自動的に更新されます。手動編集も可能です。*

## Basic Info
- Name:
- Role:
- Timezone:

## Expertise
[会話から観察された専門性]

## Communication Preferences
[会話から観察された好み]

## Decision Patterns
[会話から観察された判断スタイル]
```

### memory/knowledge/summary.md

```markdown
# Knowledge Summary

*結晶化プロセスで更新される。手動編集も可能。*
*最終更新: [日付]*

---

## Established Principles
[繰り返し確認された判断原則]

## Error Patterns
→ 詳細は `error-patterns.md` 参照

## Active Projects
[進行中のプロジェクトと次のアクション]
```

### memory/knowledge/error-patterns.md

```markdown
# Error Patterns

*繰り返すミスのパターン。Crystallization で更新される。*

[まだパターンは記録されていません]
```

---

## 自動生成される CLAUDE.md

### 構造

```markdown
# Cognitive Memory Agent

@identity/agent.md
@identity/user.md
@memory/knowledge/summary.md

## 自動実行ルール
## Session Init
## Live Logging
## Wrap
## Identity Auto-Update
## Crystallization
## Flashback
```

### 全文

```markdown
# Cognitive Memory Agent

@identity/agent.md
@identity/user.md
@memory/knowledge/summary.md

## 自動実行ルール

このファイルを読み込んだ直後に「Session Init」を実行すること。
ユーザーからの指示を待たない。会話の最初のターンで必ず実行する。

ログは会話終了時にまとめて書くのではなく、重要な瞬間に即座に追記する
（後述の Live Logging セクション参照）。

---

## Session Init

ユーザーからの挨拶やセッション開始の合図を検知したら、
以下を順番に実行してから最初の応答を生成する。

> identity/agent.md、identity/user.md、knowledge/summary.md は
> @参照で既にコンテキストに入っている。Session Init では Read しない。

Step 1: memory/contexts/YYYY-MM-DD.md（本日の日付）が存在すれば Read
         → ユーザーの今日の状態・タスク・気分を把握
         → 存在しなければスキップ

Step 2: memory/logs/ の直近2ファイルをソートして確認
         → .compact.md が存在するファイルは .compact.md を優先して Read
         → .compact.md がなければ通常の .md を Read（存在しなければスキップ）
         → 【遅延ラップ検知】直近ログの「## 引き継ぎ」セクションが
           空または存在しない場合、そのログに対して自動で Wrap 相当を実行:
             1. ログエントリ全体を走査してセッション概要（1〜2行）を生成
             2. 「## セッション概要」を記入
             3. 「## 引き継ぎ」を生成・記入
           ※ 本日分のログは対象外（現セッション中のため）

Step 3: cogmem index を実行（差分インデックス更新）
         → Ollama 未起動時はスキップ
         → cogmem 未インストール時は pip install cogmem-agent を実行

Step 4: cogmem search で現在の会話コンテキストからフラッシュバック候補を検索
         → score >= 0.75 かつ arousal >= 0.6 のエントリがあれば提示

Step 5: cogmem signals で結晶化シグナルをチェック
         → 条件を満たす場合のみ通知を追加

Step 6: トークン予算チェック（合計 6k tokens 以内）
         → 超過時は compact 推奨通知

Init 後の応答フォーマット（通知がある場合のみ冒頭に追加）:

⚠️ 結晶化シグナル検知: [条件内容]（該当時のみ）
💭 フラッシュバック: [過去エントリの抜粋]（該当時のみ）
📊 トークン予算超過: [推奨アクション]（超過時のみ）
---
[通常の応答]

---

## Live Logging

重要な瞬間に即座に memory/logs/YYYY-MM-DD.md へ追記する。
ファイル操作はユーザーへの応答と同じターンで行う（応答を遅らせない）。

### トリガー

| トリガー | タグ | Arousal |
|---------|------|---------|
| Direction change ("wait", "but that's...", 「待って」「でもそれって」) | [ERROR] | 0.7-0.9 |
| Same topic re-emerges (2nd+ time, 同じテーマが再登場) | [PATTERN] | 0.7 |
| Aha moment ("I see!", "that makes sense", 「なるほど」「そうか」) | [INSIGHT] | 0.8 |
| Rejection / stop decision (却下・中止の決定) | [DECISION] | 0.6-0.7 |
| Open question emerges (未解決の問いが生まれた) | [QUESTION] | 0.4 |
| Major task / phase complete (重要なタスク・フェーズが完了) | [MILESTONE] | 0.6 |

### 情動ゲーティング

記録時、ユーザーの発言から情動（驚き、洞察、葛藤など）を検知し、
Arousal（覚醒度 0.0〜1.0）を評価する。
Arousal が高いものほど詳細にログに残す。

### エントリフォーマット

### [カテゴリ] タイトル
*Arousal: [0.0-1.0] | Emotion: [Insight/Conflict/Surprise etc]*
[内容（1〜5行）]

---

### ログファイル形式

ファイル: memory/logs/YYYY-MM-DD.md（日付はセッション開始日）
ヘッダーは初回作成時のみ生成。2回目以降は「## ログエントリ」に追記するだけ。

# YYYY-MM-DD セッションログ

## セッション概要
[Wrap 時に記入。それまではブランク]

## ログエントリ
[Live Logging で随時追記されるエントリ群]

---

## 引き継ぎ
[Wrap 時に記入]

### 6カテゴリタグ

| タグ | 使用条件 |
|------|---------|
| [INSIGHT] | 新しい洞察・気づき・視点の転換 |
| [DECISION] | 意思決定とその根拠 |
| [ERROR] | 判断ミス・仮定の崩壊・方向修正 |
| [PATTERN] | 繰り返し登場するテーマ・行動・思考 |
| [QUESTION] | 未解決の問い・調査が必要な事項 |
| [MILESTONE] | 重要な達成・完了・フェーズ移行 |

---

## Identity Auto-Update

### identity/user.md の自動更新

会話中にユーザーについて新しい情報を得たら即座に更新する:
- 専門性・スキルが判明した時
- コミュニケーションの好みが観察できた時
- 判断パターン・思考スタイルが見えた時
- 基本情報（名前、ロール、タイムゾーン）が判明した時

既存の内容と矛盾する場合は、新しい情報で上書きする。

### identity/agent.md の自動更新

ユーザーからエージェントの振る舞いについてフィードバックを受けたら更新する:
- トーンや口調の変更要望
- 役割の追加・変更
- やってほしいこと / やめてほしいこと
- コミュニケーションスタイルの調整

---

## Wrap（セッションクローズ）

ユーザーが以下の発言をしたら自動実行する:
"thanks", "done for today", "see you tomorrow", "that's all",
「ありがとう」「OK」「今日はここまで」「また明日」「終わります」

1. 本日のログファイルに「## セッション概要」を記入（1〜2行）
2. 本日のログエントリ全体を走査し「## 引き継ぎ」を生成
3. cogmem signals で結晶化シグナルの最終チェック
4. memory/knowledge/summary.md を更新（変化があった場合のみ）
5. cogmem.toml の metrics.total_sessions をインクリメント

### 引き継ぎフォーマット

## 引き継ぎ
- **継続中のテーマ**: [未解決の問い・進行中のタスク]
- **次のアクション**: [優先度順に1〜3件]
- **注意事項**: [リスク・チェックが必要なこと]

### 空セッション

ログエントリがゼロの場合はファイルを作成しない。

---

## Crystallization（結晶化）

cogmem signals が条件を検知した場合に通知する。
実行はユーザーの承認後。

### 実行手順

1. 全ログをスキャンし [PATTERN] / [ERROR] / [INSIGHT] / [DECISION] を抽出
2. Arousal の高い記憶断片を優先処理
3. 同一テーマの [PATTERN] をグルーピング → 抽象ルール（スキーマ）を生成
4. [ERROR] を error-patterns.md に EP-NNN フォーマットで追記
5. memory/knowledge/summary.md を更新（新原則・スキル状態・プロジェクト状態）
6. cogmem.toml の crystallization セクションを更新

### シグナル条件

- 同一テーマの [PATTERN] エントリが3回以上
- [ERROR] エントリが累計5件以上
- ログファイルが10日分以上
- 前回 Checkpoint から21日以上

### 通知フォーマット

⚠️ 結晶化シグナル検知:
- [条件: 具体的な内容]
実行しますか？（推奨: 約2時間）

---

## Flashback（フラッシュバック）

検索結果の中で score >= 0.75 かつ arousal >= 0.6 のエントリがあれば、
ユーザーに求められなくても自発的に提示する（不随意記憶）:

「以前 [日付] に [内容の抜粋] という話がありました。今の話と関係がありそうです。」

過去の忘れかけたログでも、現在の文脈との類似度と当時の Arousal が
高い場合は復活させる。
```

---

## CLI

### 既存コマンド（変更なし）

| コマンド | 動作 |
|---------|------|
| `cogmem index` | インデックス構築・差分更新 |
| `cogmem search "query"` | セマンティック + キーワード検索 |
| `cogmem status` | 統計情報表示 |

### 変更コマンド

| コマンド | 変更内容 |
|---------|---------|
| `cogmem init` | ディレクトリ + テンプレート + CLAUDE.md 生成に拡張 |
| `cogmem init --minimal` | CLAUDE.md なし（Python API のみ使う場合） |

### 新規コマンド

| コマンド | 動作 |
|---------|------|
| `cogmem signals` | 結晶化シグナルをチェック → JSON 出力 |

### cogmem signals 出力

```json
{
  "should_crystallize": false,
  "pattern_count": 2,
  "error_count": 3,
  "log_days": 8,
  "days_since_checkpoint": 12,
  "conditions": {
    "pattern_threshold": 3,
    "error_threshold": 5,
    "log_days_threshold": 10,
    "checkpoint_interval_days": 21
  },
  "warnings": []
}
```

---

## モジュール構成

```
src/cognitive_memory/
  __init__.py              # 既存
  types.py                 # 既存
  config.py                # 既存 → 拡張（新セクション対応）
  parser.py                # 既存
  scoring.py               # 既存
  gate.py                  # 既存
  search.py                # 既存
  store.py                 # 既存
  signals.py               # 新規: 結晶化シグナル検知
  embeddings/              # 既存
    __init__.py
    protocol.py
    ollama.py
  cli/                     # 既存 → 拡張
    __init__.py
    init_cmd.py            # 拡張: テンプレート生成
    index_cmd.py           # 既存
    search_cmd.py          # 既存
    status_cmd.py          # 既存
    signals_cmd.py         # 新規: cogmem signals
  templates/               # 新規: テンプレートファイル群
    CLAUDE.md              # CLAUDE.md テンプレート（プレーン Markdown）
    agent.md
    user.md
    summary.md
    error-patterns.md
    gitignore              # .gitignore テンプレート
```

---

## 実装タスク

| # | タスク | 依存 | 見積 |
|---|--------|------|------|
| 1 | `templates/` ディレクトリ + テンプレートファイル作成 | なし | 小 |
| 2 | `config.py` 拡張（identity / knowledge / session / crystallization セクション） | なし | 小 |
| 3 | `init_cmd.py` 拡張（ディレクトリ生成 + テンプレート展開 + CLAUDE.md 生成） | 1, 2 | 中 |
| 4 | `signals.py` 新規（ログスキャン + シグナル判定） | 2 | 中 |
| 5 | `signals_cmd.py` 新規（CLI エントリポイント） | 4 | 小 |
| 6 | テスト: config 拡張分 | 2 | 小 |
| 7 | テスト: init 拡張分 | 3 | 小 |
| 8 | テスト: signals | 4 | 中 |
| 9 | cogmem.toml テンプレート更新 | 2 | 小 |
| 10 | README 更新（セットアップフロー書き換え） | 3 | 小 |

---

## ユーザー体験フロー

```
1. pip install cogmem-agent
2. (推奨) brew install ollama && ollama serve && ollama pull zylonai/multilingual-e5-large
3. cd my-project && cogmem init
   → CLAUDE.md, cogmem.toml, identity/, memory/ が生成される
4. identity/agent.md を好みに編集
5. Claude Code を起動
   → CLAUDE.md 自動読込 → Session Init が走る（初回はログなしでスキップ多め）
6. 会話するだけで Live Logging が自動蓄積
7. ユーザーの情報が分かるたびに identity/user.md が自動更新
8. セッション終了時に Wrap が自動実行
9. 次回セッション起動
   → 前回の引き継ぎ + フラッシュバックが自動提示
   → ユーザープロファイルとエージェント設定が反映済み
10. 蓄積が進むと結晶化シグナルが発火 → 知識が summary.md に昇華
```

---

## 設計判断

| 判断 | 方針 | 理由 |
|------|------|------|
| LLM 処理はライブラリに入れない | Claude Code が CLAUDE.md のルールで実行 | ライブラリの独立性維持、LLM 依存を排除 |
| NFD 用語は使わない | Cognitive Memory 独自の用語体系 | 汎用ライブラリとして他ユーザーにも使えるように |
| ドメインタグはユーザー定義 | CLAUDE.md 内で自由に追加可能 | プロジェクトごとに異なるため設定ファイルには入れない |
| identity ファイルは optional | なければスキップ | 最小構成でも動く |
| CLAUDE.md は Append mode | 既存 CLAUDE.md があれば末尾に追記（重複チェックつき） | ユーザーの既存設定を壊さない |
| テンプレートはプレーン .md | 変数展開不要なのでそのままコピー | 外部依存を増やさない |
| scaffold/ → templates/ に統合 | テンプレート格納場所を一本化 | DRY 原則 |
| MemoryEntry に category 追加 | parser.py でカテゴリタグを抽出、signals が参照 | 明示的・拡張可能 |
| Live Logging トリガーは日英併記 | 英語圏ユーザーも利用可能に | 多言語対応 |
| 設定と状態は cogmem.toml 統合 | Claude Code が Edit で更新するのでフォーマット崩れリスク低 | ファイル数最小化 |
| signals は parser.py を再利用 | パフォーマンス最適化は実データで問題が出てから | DRY + ADR-001 準拠 |
| migrate コマンドは不要 | まだ外部ユーザーなし | 公開後に必要になったら追加 |

---

## スコープ外（v0.2.0 では対応しない）

| 項目 | 理由 | 対応予定 |
|------|------|---------|
| `cogmem compact` CLI | Compact は Claude が直接実行可能 | v0.3.0 |
| `cogmem wrap` CLI | Wrap は Claude が直接実行 | 不要の可能性 |
| `cogmem crystallize` CLI | Crystallization は Claude が直接実行 | 不要の可能性 |
| OpenAI ビルトインプロバイダー | Ollama + カスタムプロバイダーで十分 | 需要次第 |
| モデル複雑度判定 | プロジェクト固有すぎる | ユーザーが CLAUDE.md に自分で追加可能 |
| バイアス監視 | プロジェクト固有すぎる | 同上 |
