# Knowledge Sharding — Design Spec

## Overview

`memory/knowledge/` の本文層（insights / error-patterns / principles）を単一の append-only ファイルから
**分野別シャード**へ分割し、あわせて knowledge を `vectors.db` の索引対象に加える。

**目的:** 結晶化知識が「書き込み専用アーカイブ」になっている状態を解消し、並列 worktree 運用で
多発する wrap 時コンフリクトを縮小する。

対象バージョン: cogmem-agent 0.34.0

## Background — 測定値

benchmark_app（27 worktree で並列開発）での実測:

| ファイル | サイズ | エントリ数 | 平均 | 直近200コミットでの変更回数 |
|---|---|---|---|---|
| `knowledge/insights.md` | 180,346 字 / 1,727 行 | 149 (INS-NNN) | 1,210 字 | 89 |
| `knowledge/error-patterns.md` | 134,729 字 / 1,082 行 | 117 (EP-NNN) | 1,151 字 | 78 |
| `knowledge/principles.md` | 59,774 byte | 22 セクション | — | 4 |
| `knowledge/summary.md` | 3,542 byte | — | — | 149 |

索引層（`summary*.md`）は issue #1692 で既に解決済み:
入口 `summary.md` + 分野別 `summary-{backend,frontend,devtools,testing}.md`、
1 ファイル 8,192 byte 上限を `.githooks/pre-commit` → `scripts/check-summary-size.mjs` が強制。
本 spec は**索引層には手を触れない**。未解決の本文層だけを対象にする。

### 解くべき問題

| ID | 問題 | 根拠 |
|---|---|---|
| P1 | 本文が単一 append-only ファイルで、並列 worktree の末尾追記が衝突する | `7c0863551 merge: resolve memory/* conflicts`、`93f1c7ef1 (parallel-rebased)` 等のコンフリクト解決コミットが実在 |
| P2 | 315,000 字の結晶化知識が検索不能 | `store.index_all()` は `logs_paths` のみを glob。`knowledge_insights_path` / `knowledge_error_patterns_path` は `config.py` に定義があるだけで `src/` 内に参照ゼロ |
| P3 | 圧縮が全体再読になる | 単一ファイルなので再要約の単位が 334KB |
| P4 | crystallize の重複チェックが肥大ファイルへの grep | crystallize SKILL.md:46 |
| P5 | パスの split-brain | crystallize SKILL.md:45,63 は `memory/insights.md`、`config.py:38` は `memory/knowledge/insights.md`。ember に両方実在（4,480 byte と 15,314 byte） |

## Scope

| 含む | 含まない |
|---|---|
| 本文層のシャード化 | 索引層（`summary*.md`）の変更 |
| knowledge の `vectors.db` 索引 | ログ側のスコアリング変更 |
| 移行 CLI | `check-summary-size.mjs`（benchmark_app ローカル資産） |
| crystallize / wrap スキルの追記先変更と P5 修正 | 1 エントリ 1 ファイル化（方式B、YAGNI） |

## Architecture

### レイアウト

```
memory/knowledge/
├── summary.md            # 既存。常時ロード、8KB 上限。変更なし
├── summary-{分野}.md      # 既存。索引。変更なし
├── insights/             # 新: 本文シャード
│   ├── backend.md
│   ├── frontend.md
│   ├── devtools.md
│   ├── testing.md
│   └── _unsorted.md      # 分類できなかったエントリの退避先
├── error-patterns/
│   └── {同じ分野名}.md
└── principles/
    └── {同じ分野名}.md
```

**分野名は `summary-*.md` と 1:1 で揃える。** 新しい分類軸を作らない。
追記時の「どの分野か」の判断が索引側と本文側で一回で済む。

ただしこれは**規約であってライブラリの制約ではない**。`knowledge.py` は
`knowledge/{kind}/*.md` を glob するだけで、分野名が索引層と対応しているかを検証しない。
1:1 を作るのは `migrate-knowledge` の既定動作（既存の `summary-*.md` からシャード名を導出する）と
crystallize スキルの手順であり、索引層を持たないプロジェクトでも本 spec は成立する。

**採番レジストリを置かない。** `INS-NNN` / `EP-NNN` の一意性はシャード横断 grep で最大値を取る。
レジストリファイルは全 append が触るため、P1 を別の場所に再生産する。
**不変条件: 1 回の追記が触るファイルは「該当分野の本文 1 つ + 該当分野の索引 1 行」だけ。**

**分野語彙はライブラリに持たせない。** cogmem-agent は汎用のため backend/frontend を固定語にしない。
`knowledge/insights/*.md` を glob して見つかったものが分野。`cogmem init` の初期状態は `general.md` 1 枚。

### 後方互換

設定キー（`knowledge_insights` 等）は 1 つのまま、指す先で分岐する。

| 設定が指す先 | 動作 |
|---|---|
| ファイル（既存 `memory/knowledge/insights.md`） | 単一シャードのレガシーモード。従来通り動作し、health が一度警告 |
| ディレクトリ | シャードモード |

既存ユーザーは何もしなくても壊れない。移行は CLI で明示的に行う。

## Components

### New Files

```
src/cognitive_memory/
├── knowledge.py                  # シャード解決 / knowledge パーサ / 採番 / health
└── cli/migrate_knowledge_cmd.py  # cogmem migrate-knowledge
```

`knowledge.py` の公開関数:

| 関数 | 責務 |
|---|---|
| `resolve_shards(config, kind)` | ファイルなら `[そのファイル]`、ディレクトリなら `sorted(glob("*.md"))`。互換分岐はここだけに閉じる |
| `parse_knowledge_entries(text, path)` | `## (INS\|EP)-NNN: タイトル` で分割。日付は `- **発見**: YYYY-MM-DD` から抽出、無ければ `None` |
| `next_entry_number(config, kind)` | シャード横断で最大 NNN を取る。採番の一意性はここが唯一の責任者 |
| `check_knowledge_health(config)` | シャード別サイズを返す |

`parser.parse_entries`（ログ用、h3 + `Arousal:` 前提）は変更しない。**別パーサにする** —
同じ関数に両書式を押し込むと、どちらの変更も他方を壊す。

### Modified Files

| ファイル | 変更 |
|---|---|
| `config.py` | `knowledge_principles` キー新設、`knowledge_arousal`（既定 0.6）、`shard_warn_kb` |
| `store.py` | スキーマ拡張、`index_knowledge_file()` 追加、`index_all()` が knowledge も回す |
| `search.py` | knowledge 行の `time_decay` を 1.0 に固定 |
| `types.py` | `SearchResult.kind` 追加 |
| `summary_health.py` | knowledge health を併せて報告 |
| `signals.py` | health 出力に knowledge を含める |
| skills: crystallize / wrap | 追記先をシャードに変更、P5 の split-brain 修正 |

### スキーマ変更

既存の `ALTER TABLE memories ADD COLUMN` 移行ループに乗せる。

| カラム | 型 | 意味 |
|---|---|---|
| `kind` | `TEXT DEFAULT 'log'` | `'log'` / `'knowledge'`。既存行は自動的に `'log'` に埋まる（今日 knowledge は索引されていないので正しい） |
| `source` | `TEXT` | シャードの相対パス |

これで既存コードの 3 つの制約が解ける:

1. `index_file` はファイル名から日付を取り、マッチしないと `return 0` する
   → `index_knowledge_file()` を別実装にして回避
2. stale 削除が `DELETE FROM memories WHERE date = ?` と日付キー
   → ログは `WHERE date = ? AND kind='log'`、knowledge は `WHERE source = ? AND kind='knowledge'`。
   日付衝突が構造的に起きなくなる
3. `indexed_files` の PK が basename のみ
   → knowledge 側は相対パス（`knowledge/insights/backend.md`）を PK にする

### スコアリング

knowledge 行は `time_decay = 1.0` 固定。結晶化知識は古くならないため減衰させない。
arousal は `knowledge_arousal`（既定 0.6）。

`SearchResult.source` は "semantic" / "grep" という**取得手段**の意味なので、
そこに "knowledge" を混ぜない。**内容の種別**は新設の `kind` が持つ。

## Data Flow

### 索引

`cogmem index` が `logs_paths` に加えて knowledge シャードを回す。mtime スキップは既存と同じ。

### 検索

意味検索は全行 1 回のスキャン（現状も Python 側で全行 cosine なので経路は不変）。
knowledge 行のみ decay を掛けない。結果は `kind` を持つ。

**既定 ON。** 既存プロジェクトの recall 結果に結晶化知識が混ざり始める（benchmark_app で 266 件増）。
挙動変更として大きいため CHANGELOG に明記する。

### 追記（crystallize）

1. `next_entry_number()` でシャード横断採番
2. 分野を決める（`summary.md` の「索引の地図」と同じ判断、一回だけ）
3. 本文を `knowledge/{kind}/{分野}.md` に追記
4. 索引 1 行を `summary-{分野}.md` に追記

**P4 は副産物で解決する。** knowledge が索引済みになれば、重複候補は肥大ファイルへの grep ではなく
**既存 knowledge への意味検索**で引ける。P4 は個別対処せず、P2 を直した結果として消える。

### 圧縮

`check_knowledge_health()` が伸びたシャードを名指しする。再要約の対象は全体ではなく該当シャード。

### コンフリクト（P1）への効果

完全には消えない。分野が違えば別ファイルなので衝突しないが、
**同一分野への同時追記は依然として末尾で衝突する**。

効果は「27 worktree 全部が 1 ファイルを取り合う」から
「同じ分野を触った 2 セッションだけが衝突し、1/N サイズなので解決が軽い」への縮小。
ゼロにするには方式B（1 エントリ 1 ファイル）が必要だが、266 件規模では分割のオーバーヘッドが利得を上回る。

## Migration

```
cogmem migrate-knowledge [--kind insights|error-patterns|principles|all] [--dry-run]
```

フラットファイルを読んでエントリに分割し、分野を割り当てて各シャードへ振り分ける。

分野の割り当ては **既存の埋め込みモデル（Ollama ローカル）による最近傍分類**で行う。
各分野のシード文は `summary-{分野}.md` の本文とし、エントリの埋め込みとの cosine が最大の分野に割り当て、
しきい値未満は `_unsorted.md` へ送る。

生成 LLM のクライアントは新設しない（`embeddings/ollama.py` は埋め込み専用で、生成経路は既存コードに無い）。
埋め込みだけで済ませることで、外部 API を使わず、`MockEmbedder` で決定的にテストできる。

### 論文からの意図的な逸脱

Corpus2Skill（arXiv:2604.14572）の compile フェーズは embed → K-Means → LLM がラベルを生成する。
本 spec は**クラスタリングもラベル生成もしない**。`summary-*.md` という人間が書いた分類が既に存在するため、
やるのは既存ラベルへの分類だけ。

これにより論文最大の失敗モード（上位クラスタ要約が同一ラベルに潰れ、エージェントが枝を区別できなくなる
TatQA パターン。論文 §5.3 および p=20 の ablation で F1 0.456→0.382、ハルシネーション 24.5%）が
構造的に発生しない。error-patterns の均質性リスクは、ラベルを生成しないことで消える。

### 安全策

- `--dry-run` が「どのエントリをどの分野に置くか」の対応表を出す。目視してから適用
- `memory/knowledge/` が dirty なら実行拒否（worktree の未コミット追記を巻き込まないため）
- 書き込みは temp → atomic rename
- 冪等。シャード済みレイアウトに対しては no-op

## Error Handling

| 事象 | 挙動 |
|---|---|
| 分類できないエントリ | `_unsorted.md` へ退避。**捨てない**（結晶化知識を失わないことを最優先） |
| 索引中に Ollama が落ちた | 既存の FailOpen（`[SKIP] embed failed`）のまま。変更しない |
| 移行中に Ollama が落ちた | temp のまま中断。元ファイルは無傷 |
| レガシーモード | そのまま動作。health が一度だけ警告 |
| シャード間で NNN が重複 | `next_entry_number` が max+1 を返し、signals が警告 |

**本文シャードにサイズ上限は掛けない。警告のみ。**
#1692 の構造では索引が溢れたら本文へ移す。本文は受け止める側であり、
ここに上限を置くと逃がし先が無くなる。

## Testing

`tests/fixtures/` に実データ形状の fixture を置く。

| テスト | 内容 |
|---|---|
| パーサのゴールデン | `- **発見**: YYYY-MM-DD` の有無、両方 |
| **日付衝突の回帰** | 日付 D のログを索引 → 同日付の knowledge を索引 → ログを再索引 → knowledge 行が生存すること。現行コードでは消える |
| basename 衝突 | `logs/backend.md` と `knowledge/insights/backend.md` が別行として扱われること |
| 減衰 | knowledge 行のスコアが経過日数に依存しないこと |
| レガシーモード | フラットファイルを指す設定で索引・検索が従来通り動くこと |
| 移行の往復 | フラット → 移行 → シャードでエントリ件数と本文が保存されること |
| 移行の冪等性 | 二度流して結果が変わらないこと |

## References

- issue #1692（benchmark_app）— 索引層の分割と個別上限。本 spec はその本文層への延長
- `scripts/check-summary-size.mjs`（benchmark_app）— 「分割 + 個別上限」「上限を上げるのは解ではない」「合計に上限を掛けない」の設計根拠
- Corpus2Skill: Distilling Enterprise Knowledge into Navigable Agent Skills for QA and RAG
  (Sun, Wei, Hsieh; arXiv:2604.14572v4; EMNLP 2026 Findings) — progressive disclosure の枝設計と失敗モード
