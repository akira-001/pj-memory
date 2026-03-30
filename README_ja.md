# Cognitive Memory

[English](https://github.com/akira/cognitive-memory/blob/main/README.md)

AIエージェントのための人間らしい認知的記憶 — 情動ゲーティングと適応的忘却。

従来のベクトルDBはすべての記憶を均等に扱います。Cognitive Memoryは人間の記憶の仕組みを模倣し、感情的に重要な体験はより長く残り、日常的な情報は自然に薄れていきます。これにより、AIエージェントがより自然で文脈を理解した振る舞いをします。

## 主な特徴

- **情動ゲーティング**: Arousalスコアが記憶の持続性を調整
- **適応的忘却**: 高Arousalの記憶ほどゆっくり減衰（半減期を設定可能）
- **適応検索ゲート**: 挨拶などの些末なクエリを自動スキップ
- **コンテキスト検索**: トピック検知 + セッションキャッシュ + フラッシュバックフィルタリング
- **FailOpen設計**: エンベディングが利用不可の場合はキーワード検索にフォールバック
- **外部依存ゼロ**: コアはPython標準ライブラリのみ使用（sqlite3, urllib）
- **プラガブルなエンベディング**: Ollama（組み込み）、OpenAI、または任意のカスタムプロバイダー
- **想起強化**: 想起された記憶はAroualブースト（+0.1）とrecall_countが増加 — 人間の記憶固定化と同様
- **鮮明なエンコーディング**: 高ArousalのイベントはAroualに連動した豊かな文脈で記録（因果関係、別名、ユーザー発言の引用）
- **デジャヴ認識**: 依頼内容が過去の作業にマッチした場合に自動検知し、自然に案内
- **スキル学習システム**: スキルの使用を追跡し、改善機会を検出し、新スキルを自動生成
- **Gitヒストリー分析**: `cogmem watch` がコミットパターンを分析し、ワークフロー習慣とプロトコルの抜けを検出
- **アイデンティティ管理**: エージェントの人格（`soul.md`）とユーザープロファイル（`user.md`）を自動更新
- **SUMMARYインデックス**: セッション概要を専用カテゴリでインデックス化し、「何をなぜやったか」を横断検索可能
- **Webダッシュボード**: FastAPI + HTMX ダッシュボードで記憶・スキル・ログ・人格を閲覧（EN/JA対応）

## なぜ Cognitive Memory？

従来のRAGやベクトルDBは、テキストの類似度だけで記憶を検索します。すべての記憶が等しく扱われ、何気ない挨拶と重要なビジネス判断が同じ重みを持ちます。その結果、ノイズが多く文脈の薄い検索結果になり、AIエージェントが機械的に感じられます。

Cognitive Memory は人間の認知の3つの側面をモデル化することで、これを変えます:

### 1. 情動ゲーティング

各記憶エントリは **Arousalスコア**（0.0〜1.0）を持ち、感情的な強度（驚き、洞察、葛藤、決意など）を反映します。高Arousalの記憶は検索結果でより重く評価されます。

| クエリ | 従来のベクトルDB | Cognitive Memory |
|-------|----------------|-----------------|
| "過去の価格決定" | "価格"に言及するすべての記憶をテキスト類似度順で返す | 価格戦略を覆した激しい議論（arousal: 0.9）を、定期的な価格更新ログ（arousal: 0.2）より優先する |

**どんな会話が高Arousalとして記憶される？** 感情的・認知的に重要な瞬間:

| 会話例 | Arousal | なぜ重要か |
|-------|---------|----------|
| 「待って、その前提おかしくない？」 | 0.9 | 方向転換 — 仮定の崩壊 |
| 「なるほど、そういうことか！」 | 0.8 | 腑に落ちた瞬間 — 認知的ブレイクスルー |
| 「この方向でやめよう。理由は〜」 | 0.7 | 却下判断 — 意思決定の転換点 |
| 「これ3回目だね、同じ話」 | 0.7 | 繰り返しの認識 — メタ認知 |
| 「Phase 1 完了した」 | 0.6 | 達成 — フェーズ移行 |
| 「〜について調べる必要があるな」 | 0.4 | 未解決の問いが生まれた |

これらは記憶されます。一方、挨拶（「おはよう」）、相槌（「OK」）、進行指示（「次に進もう」）はスコアがほぼ0で、適応検索ゲートによって自動的にスキップされます。

### 2. 適応的忘却

記憶は時間とともに減衰しますが、均一ではありません。減衰の半減期はArousalに適応します:

```
half_life = base_half_life * (1 + arousal)
```

- 日常的なステータス更新（arousal: 0.2）の半減期は **72日** で、すぐに薄れる
- 重要なピボット判断（arousal: 0.9）の半減期は **114日** で、はるかに長く残る

エージェントはノイズを自然に「忘れ」、重要な瞬間を保持します — 人間の記憶と同じように。

### 3. 適応検索ゲート

すべてのユーザーメッセージに記憶検索が必要なわけではありません。挨拶（「こんにちは」）、相槌（「OK」）、些末なメッセージは自動的に検知してスキップします。不要なエンベディングAPI呼び出しを節約し、検索結果のノイズを減らします。

### 4. コンテキスト検索（v0.3.1）

通常の検索がオンデマンドで動くのに対し、**コンテキスト検索**は会話中に過去の記憶が現在の話題と関連するタイミングを自動検知し、「フラッシュバック」として浮上させます。エージェントは質問にただ答えるだけでなく、回答に深みを加える過去の経験を想起します。

**例1: 過去の意思決定がちょうどいいタイミングで浮上する**

2週間前にエージェントと価格モデルについて議論し、激論の末にシート課金から従量課金に切り替えた。今日:

```
ユーザー: 「エンタープライズ向けの価格モデルを考えよう」

エージェント: 「エンタープライズ向けなら従量課金が有効だよ。導入障壁が下がって、
              チームが小さく始めてスケールできる。検討ポイント:
              月$10K超のボリュームディスカウント、年間コミットで15-20%割引、
              専用サポートティア...」

💭 関連する過去の記録: 2026-03-08 [DECISION] シート課金→従量課金に変更 —
   シート課金は大規模チームにペナルティになり、拡張時の抵抗になる
   (arousal: 0.8)
```

コンテキスト検索がなければ、エージェントはエンタープライズ価格の質問にゼロから答える。コンテキスト検索があれば、過去の意思決定を踏まえた回答になり、フラッシュバックが「なぜ従量課金にしたのか」を思い出させてくれる。

**例2: 忘れかけたミスが同じ失敗を防ぐ**

3週間前、ある市場への参入を試みてタイミングが悪いことが判明した。記憶は減衰しているが、高い arousal のおかげでまだ残っている:

```
ユーザー: 「EUコンプライアンス市場への拡大はどうかな？」

エージェント: 「EU AI Actの施行は2026年Q3だから、確かにウィンドウはある。
              主な競合は...」

💭 関連する過去の記録: 2026-03-01 [ERROR] 規制タイミングへの依存が短すぎた
   （リードタイム3ヶ月未満）— 施行日がずれて候補を断念
   (arousal: 0.9)
```

エージェントは質問にそのまま答えるが、フラッシュバックが「以前、規制タイミングで痛い目を見た」というやんわりとした警告として機能する。それを踏まえて判断するかどうかはユーザー次第。

**例3: 些末なメッセージはスキップされる**

```
ユーザー: 「OK」         → ゲート: スキップ（相槌、< 1ms）
ユーザー: 「なるほど」     → ゲート: スキップ（短文、トピックパターンなし）
ユーザー: 「競合の状況を分析しよう」
                         → ゲート: 通過（「分析」+ トピックパターン）
                         → 検索実行、該当あればフラッシュバック表示
```

仕組み:
- **トピック検知**: 新しいテーマの導入を認識（「〜について」「〜の件」、設計・分析系キーワード）
- **セッションキャッシュ**: 同一会話内で重複するエンベディング呼び出しを回避（cosine similarity > 0.9 でキャッシュヒット）
- **フラッシュバックフィルタ**: 類似度（≥ 0.65）と情動的重要性（arousal ≥ 0.5）の両方を満たす結果のみ浮上
- **パフォーマンス目標**: warm 時 < 200ms、ゲートスキップ時 < 1ms

### 5. 想起強化（v0.10.0）

記憶が検索されるたびに、そのArousalが+0.1ブースト（上限1.0）され、`recall_count` がインクリメントされます。これは人間の記憶固定化をモデル化したもので、頻繁に想起される記憶は忘却に強くなります。

```python
# 検索後、マッチしたエントリは自動的に強化される:
# UPDATE memories SET recall_count = recall_count + 1,
#                     arousal = MIN(arousal + 0.1, 1.0),
#                     last_recalled = NOW()
```

### 6. スキル学習システム（v0.4.0–v0.8.0）

エージェントがスキルを使うたびに追跡し、各実行から学習します:

- **Track**: skill_start、skill_end、逸脱イベント（extra_step、skipped_step、error_recovery、user_correction）を記録
- **Learn**: タスク完了後に効果を評価し、学習データを保存
- **Audit**: パフォーマンスが低いスキル・衰退傾向・未カバーパターンを検出
- **Auto-improve**: `auto_improve = "auto"` の場合、追跡イベントに基づいてスキルファイルを自動更新

```bash
cogmem skills track "my-skill" --event skill_start --description "デプロイ開始"
cogmem skills learn --context "本番デプロイ" --outcome "成功" --effectiveness 0.9
cogmem skills audit --json --brief
cogmem skills review            # 全スキルのヘルスレポート
```

### 7. アイデンティティ管理（v0.9.0）

会話を通じて進化する2つのアイデンティティファイルを管理します:

- `identity/soul.md`: エージェントの人格 — 役割、価値観、思考スタイル、コミュニケーション好み
- `identity/user.md`: ユーザープロファイル — 専門性、意思決定パターン、興味

```bash
cogmem identity show --target user     # 現在のプロファイルを表示
cogmem identity detect --json          # プレースホルダーセクションをチェック
cogmem identity update --target user --json '{"expertise": "追加: AIエージェント設計"}'
```

アイデンティティファイルはセッションのWrap時に観察された情報に基づいて自動更新されます。

### 8. Webダッシュボード（v0.5.0–v0.10.0）

記憶・スキル・ログ・人格を閲覧するための組み込みWebダッシュボード。

```bash
pip install cogmem-agent[dashboard]
cogmem dashboard                       # http://127.0.0.1:8765 で起動
```

ページ: 記憶概要、スキル（使用統計+効果）、ログ（検索可能）、検索（ライブ）、人格、記憶定着シグナル。EN/JA完全国際化対応。

### 導入効果

| 観点 | Cognitive Memory なし | Cognitive Memory あり |
|-----|---------------------|---------------------|
| 検索品質 | すべての記憶がテキスト類似度だけで均等にランク付け | 重要な記憶が優先的に浮上し、ノイズは沈む |
| 時間経過 | 古い記憶が減衰せず、検索がどんどんノイジーに | 自然な忘却で検索結果の鮮度を維持 |
| エージェントの個性 | 汎用的で機械的な応答 | 重要だったことを覚えていて、より人間らしい |
| 無駄な検索 | すべてのメッセージでベクトル検索が発動 | 些末なメッセージは自動スキップ |
| 文脈的想起 | 手動検索のみ | 関連する過去の記憶が会話中に自動浮上 |

## ベンチマーク: 記憶がエージェントの精度を向上させる

Claude Opusを使ったA/B比較テストで、cogmemの記憶がエージェントの回答精度にどう影響するかを測定しました。30問（エラーパターン回避とプロジェクト固有の知識）を、cogmemありとなしの2つのエージェントで回答。

| | cogmemなし | cogmemあり | 改善 |
|--|-----------|-----------|------|
| **全体** | 5/30 (17%) | 12/30 (40%) | **2.4倍** |
| EPの再発 | 1/5 | 3/5 | +2 |
| 文脈依存 | 4/25 | 9/25 | +5 |

**難しい問題ほど、差が大きい:**

| 難易度 | なし | あり | cogmemの効果 |
|-------|-----|-----|-------------|
| Easy | 21% | 29% | +7% |
| Medium | 18% | 45% | **+27%** |
| Hard | 0% | 60% | **+60%** |

難問（過去の出来事からの多段階推論を要する問題）で最も劇的な改善 — 0%から60%へ。感情的に重要な記憶を適切にエンコード・検索することで、エージェントが意味のある形で賢くなることを検証しました。

> **注**: このベンチマークはcogmemの記憶検索のみをテストしています。本番環境では、行動プロトコル（`agents.md`）、人格（`soul.md`）、自動生成スキルも組み合わせて使うため、実際の効果はさらに大きくなります。

*ベンチマーク詳細: 55問のテストセット（EP再発5問 + 文脈依存50問）、キーワード採点、Claude Opus 4.6。データセットとランナーは `tests/ab_comparison/` に収録。*

## インストール

```bash
pip install cogmem-agent
cogmem init        # プロジェクト構造をスキャフォールド（下記参照）
```

`cogmem init` はClaude Code環境に2種類のツールを自動インストールします:

1. **エージェントスキル**（v0.14.0）: 5つの必須プロトコルスキルを `~/.claude/skills/` にインストール — `session-init`、`live-logging`、`skill-tracking`、`wrap`、`crystallize`。これらはエージェントの行動プロトコルを動かし、すべてのプロジェクトで共通して機能します。
2. **skill-creatorプラグイン**: [Anthropic 公式 skill-creator プラグイン](https://github.com/anthropics/claude-plugins-official)をインストール。スキルの作成・評価・改善のワークフローが利用可能になります。

### プロジェクト構造

`cogmem init` で以下の構造が生成されます:

```
your-project/
├── CLAUDE.md                    # エントリポイント — @参照のみ（16行）
├── cogmem.toml                  # 設定ファイル
├── identity/
│   ├── agents.md                # 行動ルール（Session Init, Live Logging, Wrap 等）
│   ├── soul.md                  # エージェントの人格（役割、価値観、思考スタイル）
│   └── user.md                  # ユーザープロファイル（会話から自動更新）
└── memory/
    ├── logs/                    # セッションログ（YYYY-MM-DD.md）
    ├── contexts/                # デイリーコンテキストファイル
    ├── skills.db                # スキル使用データと学習データ
    └── knowledge/
        ├── summary.md           # 結晶化された知識
        └── error-patterns.md    # 繰り返すエラーパターン
```

CLAUDE.md は最小限 — identity と knowledge ファイルへの `@参照` のみ。すべての行動プロトコルは `identity/agents.md` にあるため、フレームワークに触れずにカスタマイズできます。

### エンベディングのセットアップ（推奨）

Cognitive Memory はローカルエンベディングに [Ollama](https://ollama.com/) を使用します。Ollama がない場合はキーワード検索のみにフォールバックします。

```bash
# 1. Ollama をインストール (macOS)
brew install ollama

# 2. サーバーを起動
ollama serve

# 3. エンベディングモデルをダウンロード (~2.2 GB)
ollama pull zylonai/multilingual-e5-large
```

> 他のプラットフォーム: [ollama.com/download](https://ollama.com/download) を参照
>
> OpenAI やカスタムプロバイダーも使用可能です — [エンベディングプロバイダー](docs/embedding-providers.md) を参照。

### Ollama あり / なしの違い

Cognitive Memory はエンベディングプロバイダーの有無に応じて2つのモードで動作します:

Ollama を導入すると、検索が「完全一致のキーワード検索」から「意味を理解するセマンティック検索」に切り替わります。関連概念の発見、多言語横断検索、タイポ耐性、情動ベースのランキング、適応的忘却といった Cognitive Memory のコア機能がすべて有効になります。ローカル実行のため追加コストやプライバシーリスクはなく、ディスク約2.2GBのみで利用できます。

| | Ollama なし（キーワードモード） | Ollama あり（セマンティックモード） |
|---|---|---|
| **検索方式** | 完全一致キーワード検索（grep） | ベクトル類似度 + 情動スコアリング |
| **「価格戦略」で検索** | "価格" と "戦略" を含むエントリのみヒット | "LTV:CAC最適化"、"収益モデル"、"コスト構造" など関連エントリも発見 |
| **多言語対応** | 日本語クエリは日本語テキストのみ一致 | "価格戦略" で日本語・英語両方の価格関連エントリを発見 |
| **タイポ・同義語** | "競合分析" の誤字 → ヒットなし | 意図を理解し、競合関連のエントリを返す |
| **スコアリング** | 一致/不一致の二値 | `(0.7 * cosine_sim + 0.3 * arousal) * time_decay` でニュアンスあるランキング |
| **適応的忘却** | 利用不可（すべての一致が同等） | 古い低Arousalエントリは検索結果から自然に沈む |
| **レイテンシ** | < 1ms | ~15ms（ローカル実行、ネットワーク通信なし） |
| **プライバシー** | ローカル | ローカル — データは外部に送信されない |
| **コスト** | 無料 | 無料（Ollama はオープンソース） |
| **ディスク使用量** | 0 | ~2.2 GB（モデルの重み） |

**推奨**: Ollama をインストールして、認知的記憶のフル体験を有効にしてください。キーワードフォールバックはセーフティネットとして設計されており、主要な動作モードではありません。

## クイックスタート

### CLI

```bash
cogmem init                                  # プロジェクト初期化
cogmem index                                 # インデックスの構築・更新
cogmem search "過去の意思決定"                # 記憶を検索
cogmem signals                               # 結晶化シグナルのチェック
cogmem context-search "クエリ"               # コンテキスト検索（フラッシュバックフィルタ付き）
cogmem status                                # 統計情報を表示
cogmem migrate                               # 旧バージョンからのアップグレード
cogmem watch --since "8 hours ago"           # 直近のGit履歴を分析
cogmem skills track "skill" --event skill_start  # スキル使用を追跡
cogmem skills learn --effectiveness 0.9      # 学習データを記録
cogmem skills audit --json --brief           # スキルのヘルスチェック
cogmem skills review                         # 全スキルのヘルスレポート
cogmem identity show --target user           # アイデンティティを表示
cogmem identity update --target user         # アイデンティティを更新
cogmem recall-stats                          # 記憶の想起統計
cogmem dashboard                             # Webダッシュボードを起動
```

### 使い方: 典型的なセッションの流れ

Cognitive Memory と Claude Code を使った実際の開発セッションの流れ。

**1. Claude Code を起動する**

```bash
cd your-project     # cogmem.toml があるディレクトリ
claude              # Claude Code を起動
```

**2. 挨拶する — Session Init が自動実行される**

```
あなた: おはよう
```

エージェントが新しいセッションを検知し、**Session Init** を自動実行:
- 今日のコンテキストと直近のログを読み込み
- `cogmem index` でインデックスを更新
- 関連する過去の記憶をフラッシュバックとして検索
- 記憶の定着シグナルとスキルの健康状態をチェック

```
エージェント: おはよう、Akira。

💭 フラッシュバック: 前に認証ミドルウェアの書き換えを議論したよね。
   法務がセッショントークンの保存方法にコンプライアンス上の問題を指摘してた。
🔧 Skill audit: "deploy" スキルの effectiveness が低下中 (0.6 → 0.4)。

今日は何から進める？
```

**3. 普通に作業する — Live Logging がバックグラウンドで動く**

作業中、エージェントは重要な瞬間を自動でログに記録する:
- 方向転換、洞察、意思決定、エラー、マイルストーン
- 各エントリに情動的・認知的な重要度に基づく Arousal スコアを付与
- 高 Arousal のイベントは因果関係、別名、ユーザー発言の引用を含めて鮮明に記録

**4. コンテキストが 60% を超えたら圧縮する**

```
あなた: /compact
```

会話の過去メッセージを圧縮し、コンテキストウィンドウの空きを確保する。重要な情報は保持されるので、エージェントはそれまでの経緯を把握したまま作業を継続できる。

**5. セッションを終了する — Wrap が自動実行される**

```
あなた: ありがとう（または「今日はここまで」「done for today」など）
```

エージェントがセッション終了を検知し、**Wrap** を自動実行:
- セッション概要と引き継ぎをログに記録
- 記憶の定着シグナルをチェック（条件を満たせば自動実行）
- セッション中に使用したスキルの評価・改善
- 新しく学んだユーザー情報があれば identity ファイルを更新
- セッションカウンターをインクリメント

```
エージェント: お疲れさま。今日のログを記録したよ。

## 引き継ぎ
- **継続テーマ**: 認証ミドルウェアの書き換え（コンプライアンス対応）
- **次のアクション**: 1. トークン移行を完了  2. デプロイスクリプトを更新
- **注意事項**: deploy スキルを更新済み（ロールバック手順を追加）
```

**6. 次のセッション — エージェントは覚えている**

```bash
claude              # 新しいセッションを起動
あなた: 再開
```

エージェントは前回の引き継ぎを読み、コンテキストを検索し、中断したところから再開する。過去の決定、ミス、洞察を踏まえた上で作業を進める。

**サイクル**: 挨拶 → 作業 → 圧縮（必要に応じて） → ラップ → 繰り返し。記憶はセッションをまたいで蓄積され、エージェントは使うほど文脈を理解するようになる。

### Python API

```python
from cognitive_memory import MemoryStore, CogMemConfig

config = CogMemConfig.from_toml("cogmem.toml")
with MemoryStore(config) as store:
    store.index_dir()
    result = store.search("過去の競合分析")
    for r in result.results:
        print(f"{r.date} [{r.score:.2f}] {r.content[:80]}")
```

### コンテキスト検索（v0.3.1）

```python
from cognitive_memory import MemoryStore, SearchCache, CogMemConfig

config = CogMemConfig.from_toml("cogmem.toml")
cache = SearchCache(max_size=20, sim_threshold=0.9)

with MemoryStore(config) as store:
    store.index_dir()
    # キャッシュ付きコンテキスト検索
    result = store.context_search(
        "価格戦略の議論について",
        cache=cache,  # 呼び出し間で再利用し、重複embedを回避
        session_keywords=["価格", "LTV"],
    )
    for r in result.results:
        print(f"💭 {r.date} [{r.score:.2f}] {r.content[:80]}")
```

### 簡易API

```python
from cognitive_memory import search
result = search("過去の意思決定")  # cogmem.toml を自動検出
```

## スコアリング式

```
score = (0.7 * cosine_sim + 0.3 * arousal) * time_decay
```

`time_decay` は適応的半減期を使用:
```
half_life = base_half_life * (1 + arousal)
```

高Arousalの記憶（洞察、葛藤、驚き）はゆっくり減衰します — 人間の記憶と同じように。

## 設定

`cogmem.toml`:

```toml
[cogmem]
logs_dir = "memory/logs"
db_path = "memory/vectors.db"

[cogmem.identity]
soul = "identity/soul.md"
user = "identity/user.md"

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

[cogmem.context_search]
enabled = true
flashback_sim = 0.65        # フラッシュバックの最小コサイン類似度
flashback_arousal = 0.5     # フラッシュバックの最小Arousal
cache_max_size = 20         # セッションキャッシュの容量
cache_sim_threshold = 0.9   # キャッシュヒットの類似度閾値
```

### v0.2.0〜0.2.1 からのアップグレード

```bash
pip install --upgrade cogmem-agent
cogmem migrate
```

`cogmem migrate` が自動で実行する内容:
- `identity/agent.md` → `identity/soul.md` にリネーム
- `identity/agents.md`（行動プロトコル）を新規生成
- `cogmem.toml` と `CLAUDE.md` の参照を更新

## カスタムエンベディングプロバイダー

```python
class MyEmbedder:
    def embed(self, text: str) -> list[float] | None: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]] | None: ...

store = MemoryStore(config, embedder=MyEmbedder())
```

## ドキュメント

- [クイックスタート](docs/quickstart.md)
- [ログフォーマット](docs/log-format.md)
- [エンベディングプロバイダー](docs/embedding-providers.md)

## 参考文献

### 論文

- [NFD: Nurture-First Development](https://arxiv.org/abs/2603.10808) — 経験層と結晶化によるAIエージェントのパーソナリティ発達アーキテクチャ
- [A-MEM: Agentic Memory for LLM Agents](https://arxiv.org/abs/2502.12110) — 自律エージェントのためのアトミックノート型記憶構造化

### プロジェクト

- [memory-lancedb-pro](https://github.com/mem0ai/memory-lancedb-pro) — 適応ゲートと時間減衰パイプラインの設計参考
- [memU](https://github.com/NevaMind-AI/memU) — 経験層の実装参考
- [A-mem](https://github.com/WujiangXu/A-mem) — アトミックノートの実装参考

## ライセンス

MIT
