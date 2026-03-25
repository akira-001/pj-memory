# Skills Memory Layer - Memento-Skills Integration

cogmemライブラリにMemento-Skillsを統合したSkills Memory Layerが追加されました。

## 概要

Skills Memory Layerは以下の機能を提供します：

### 🧠 Read-Write Reflective Learning Loop
- **Read Phase**: 状況を分析し適用可能なスキルを特定
- **Execute Phase**: 最適なスキルを実行し結果を記録
- **Write Phase**: 効果を測定し改善やスキル作成を判定
- **Reflect Phase**: 学習結果から戦略的インサイトを抽出

### 📊 自動スキル管理
- パフォーマンス監視と評価
- 効果的でないスキルの自動改善
- 新しい状況に対する新スキルの自動作成
- スキルの類似性検出と重複防止

### 🎯 5つのスキルカテゴリ
- `conversation-skills`: 会話・対話関連
- `proactive-skills`: 先読み・提案関連
- `automation-skills`: 自動化・スケジューリング関連
- `learning-skills`: 学習・改善関連
- `meta-skills`: メタ認知・複合スキル関連

## インストールと設定

### 1. 必要な依存関係の確認

cogmemライブラリの標準機能に加えて、Skills Memory Layerは以下を利用します：

- SQLite3（Python標準ライブラリ）
- FTS5（全文検索）

### 2. プロジェクト初期化

```bash
# cogmemプロジェクトを初期化
cogmem init

# スキル機能を使用する準備
cogmem skills stats
```

## 基本的な使用方法

### Python APIでの使用

```python
from cognitive_memory import CogMemConfig, SkillsManager, PerformanceMetric

# 設定の読み込み
config = CogMemConfig.find_and_load()

# スキルマネージャーの初期化
skills_manager = SkillsManager(config)

# 新しいスキルの作成
performance = PerformanceMetric(
    effectiveness=0.8,      # 効果度 (0-1)
    user_satisfaction=0.7,  # ユーザー満足度 (0-1)
    execution_time=1500.0,  # 実行時間 (ms)
    error_rate=0.1          # エラー率 (0-1)
)

new_skill = skills_manager.create_skill_from_context(
    context="重要なメールに効率的に返信する",
    performance=performance,
    user_feedback="良いが、もう少し速くできるかも"
)

print(f"作成されたスキル: {new_skill.name}")
print(f"カテゴリ: {new_skill.category}")
```

### Read-Write学習ループの実行

```python
# 完全な学習ループを実行
context = "プロジェクトの締切が近づいている状況でタスクの優先順位を決める"
performance = PerformanceMetric(
    effectiveness=0.9,
    user_satisfaction=0.8,
    execution_time=2000.0,
    error_rate=0.05
)

result = await skills_manager.execute_learning_loop(
    context=context,
    performance=performance,
    user_feedback="非常に役に立った。優先順位が明確になった"
)

print(f"学習アクション: {result['write_phase']['action']}")
print(f"選択されたスキル: {result['learning_summary']['skill_selected']}")
if result['learning_summary']['key_insights']:
    print("主要な洞察:")
    for insight in result['learning_summary']['key_insights']:
        print(f"  • {insight}")
```

### スキルの検索と管理

```python
# スキルの検索
email_skills = skills_manager.search_skills("メール", top_k=5)
print(f"メール関連のスキル: {len(email_skills)}個")

for skill in email_skills:
    print(f"  - {skill.name} (効果度: {skill.usage_stats.average_effectiveness:.3f})")

# トップパフォーマンススキルの取得
top_skills = skills_manager.get_top_skills(limit=5)
print("\nトップパフォーマンススキル:")
for i, skill in enumerate(top_skills, 1):
    print(f"  {i}. {skill.name} ({skill.usage_stats.average_effectiveness:.3f})")

# スキル統計の確認
stats = skills_manager.get_skill_stats()
print(f"\nスキル統計:")
print(f"  総スキル数: {stats['total_skills']}")
print(f"  平均効果度: {stats['average_effectiveness']:.3f}")
print(f"  総実行回数: {stats['total_executions']}")
```

## CLIでの使用

### スキル一覧表示

```bash
# 全スキルの表示
cogmem skills list

# カテゴリでフィルタ
cogmem skills list --category conversation-skills

# トップ5のスキルのみ表示
cogmem skills list --top 5

# JSON形式で出力
cogmem skills list --json
```

### スキル検索

```bash
# キーワードでスキル検索
cogmem skills search "メール返信"

# カテゴリ指定検索
cogmem skills search "自動化" --category automation-skills

# 検索結果数の指定
cogmem skills search "会議" --top-k 3
```

### スキル詳細表示

```bash
# スキルの詳細情報を表示
cogmem skills show <skill_id>

# JSON形式で詳細表示
cogmem skills show <skill_id> --json
```

### 新しいスキルの作成

```bash
# 手動でスキルを作成
cogmem skills create "チームミーティングの効果的な進行" \
    --effectiveness 0.8 \
    --user-satisfaction 0.7 \
    --feedback "時間管理が改善された"
```

### 学習ループの実行

```bash
# 状況に基づいた学習ループを実行
cogmem skills learn "緊急度の高いタスクの判断と対応" \
    --effectiveness 0.9 \
    --user-satisfaction 0.8 \
    --execution-time 1200 \
    --error-rate 0.05 \
    --feedback "迅速で的確な判断ができた"
```

### スキル統計の確認

```bash
# 全体統計の表示
cogmem skills stats

# JSON形式で統計取得
cogmem skills stats --json
```

## 高度な使用例

### カスタム評価とスキル改善

```python
# 特定のスキルの詳細評価
skill = skills_manager.load_skill("conversation-skills", "skill_123")
evaluation = skills_manager.evaluate_skill(skill, recent_window_days=30)

print(f"スキル評価:")
print(f"  総合スコア: {evaluation['overall_score']:.3f}")
print(f"  成功率: {evaluation['success_rate']:.3f}")
print(f"  改善傾向: {evaluation['improvement_trend']:.3f}")
print(f"  推奨アクション: {evaluation['recommendation']}")
```

### 類似スキルの検出

```python
# 特定のコンテキストに類似するスキルを検索
similar_skills = skills_manager.find_similar_skills(
    "プレゼンテーションの準備と実行",
    threshold=0.6
)

print(f"類似スキル {len(similar_skills)}個:")
for skill in similar_skills:
    print(f"  - {skill.name}")
```

### 既存記憶システムとの統合

```python
from cognitive_memory import search

# 通常の記憶検索
memory_results = search("プロジェクト管理", top_k=5)

# 記憶結果に関連するスキルを提案
relevant_skills = skills_manager.integrate_with_memory_search(
    "プロジェクト管理",
    memory_results
)

print("関連スキル:")
for skill in relevant_skills:
    print(f"  - {skill.name} (効果度: {skill.usage_stats.average_effectiveness:.3f})")
```

## ファイル構造

Skills Memory Layerは以下のディレクトリ構造を作成します：

```
memory/
├── skills/
│   ├── conversation-skills/
│   ├── proactive-skills/
│   ├── automation-skills/
│   ├── learning-skills/
│   └── meta-skills/
├── skills.db        # スキルメタデータとFTS索引
└── ...
```

## 設定オプション

`cogmem.toml`に以下の設定を追加できます：

```toml
[skills]
# スキル作成のしきい値 (改善ポテンシャル)
creation_threshold = 0.3

# 新スキル検討の最小頻度 (週あたり)
min_frequency = 0.1

# 効果改善の最小しきい値 (15%以上の改善見込み)
improvement_threshold = 0.15

# スキル類似度のしきい値
similarity_threshold = 0.7
```

## パフォーマンス指標

Skills Memory Layerは以下の指標を追跡します：

- **効果度 (Effectiveness)**: スキルの実行成功率
- **ユーザー満足度 (User Satisfaction)**: ユーザーのフィードバックスコア
- **実行時間 (Execution Time)**: タスク完了までの時間
- **エラー率 (Error Rate)**: 実行中のエラー発生率
- **頻度 (Frequency)**: スキルの使用頻度
- **改善履歴 (Improvement History)**: 時系列での性能改善記録

## トラブルシューティング

### よくある問題

1. **FTSエラー**: SQLiteのFTS5が有効でない場合
   - 解決策: 新しいバージョンのSQLiteを使用

2. **検索でスキルが見つからない**: 新規作成後すぐの検索
   - 解決策: データベースの更新を待つか、IDで直接アクセス

3. **パフォーマンスが遅い**: 大量のスキルがある場合
   - 解決策: 定期的な不要スキルの削除とデータベース最適化

### デバッグ情報の取得

```python
# デバッグ情報付きでスキル作成
import logging
logging.basicConfig(level=logging.DEBUG)

# スキルマネージャーの詳細ログを確認
skills_manager = SkillsManager(config)
# ログでスキルの内部動作を確認可能
```

## 今後の拡張予定

- 🔄 スキルのバージョン管理とロールバック
- 🤖 LLMとの連携によるスキル記述の自動生成
- 📈 より高度なパフォーマンス分析とレポート
- 🔗 他のcogmem機能との深い統合
- 🎯 ユーザー固有のスキル学習パターン分析

## 参考文献

このSkills Memory Layerは以下の研究に基づいています：

- **Memento-Skills**: Self-reflective agents for lifelong learning
- **Read-Write Reflective Learning**: Continuous improvement through reflection
- **Cognitive Memory**: Human-like memory for AI agents

---

*cogmemライブラリのSkills Memory Layer - あなたのAIエージェントが経験から学習し、スキルを自動的に獲得・改善する力を提供します。*