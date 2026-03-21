# Cognitive Memory

[English](README.md)

AIエージェントのための人間らしい認知的記憶 — 情動ゲーティングと適応的忘却。

従来のベクトルDBはすべての記憶を均等に扱います。Cognitive Memoryは人間の記憶の仕組みを模倣し、感情的に重要な体験はより長く残り、日常的な情報は自然に薄れていきます。これにより、AIエージェントがより自然で文脈を理解した振る舞いをします。

## 主な特徴

- **情動ゲーティング**: Arousalスコアが記憶の持続性を調整
- **適応的忘却**: 高Arousalの記憶ほどゆっくり減衰（半減期を設定可能）
- **適応検索ゲート**: 挨拶などの些末なクエリを自動スキップ
- **FailOpen設計**: エンベディングが利用不可の場合はキーワード検索にフォールバック
- **外部依存ゼロ**: コアはPython標準ライブラリのみ使用（sqlite3, urllib）
- **プラガブルなエンベディング**: Ollama（組み込み）、OpenAI、または任意のカスタムプロバイダー

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

### 導入効果

| 観点 | Cognitive Memory なし | Cognitive Memory あり |
|-----|---------------------|---------------------|
| 検索品質 | すべての記憶がテキスト類似度だけで均等にランク付け | 重要な記憶が優先的に浮上し、ノイズは沈む |
| 時間経過 | 古い記憶が減衰せず、検索がどんどんノイジーに | 自然な忘却で検索結果の鮮度を維持 |
| エージェントの個性 | 汎用的で機械的な応答 | 重要だったことを覚えていて、より人間らしい |
| 無駄な検索 | すべてのメッセージでベクトル検索が発動 | 些末なメッセージは自動スキップ |

## インストール

```bash
pip install cogmem-agent
cogmem init        # cogmem.toml, identity/, memory/, CLAUDE.md をスキャフォールド
```

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
cogmem init                        # プロジェクト初期化
cogmem index                       # インデックスの構築・更新
cogmem search "過去の意思決定"       # 記憶を検索
cogmem signals                     # 結晶化シグナルのチェック
cogmem status                      # 統計情報を表示
```

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
