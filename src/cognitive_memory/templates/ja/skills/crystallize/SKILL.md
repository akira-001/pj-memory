---
name: crystallize
description: 経験の結晶化。ログから知識を抽出し、スキルとメモリに統合する（NFD Algorithm 1）
user-invocable: true
---

# SKILL: Crystallize — 経験の結晶化

*NFD Algorithm 1 の実装。ログから知識を抽出し、スキルとメモリに統合する。*

## 実行条件

- Akiraから明示的に指示された場合
- `AGENTS.md` の結晶化シグナルが発火した場合（自動通知）

## 入力

1. `memory/logs/YYYY-MM-DD.md`（指定期間または全期間）
2. `memory/MEMORY.md`（現在の結晶化済み知識）
3. 対象ドメインスキルの `SKILL.md`

## 実行手順

### Step 1: ログスキャン（Read）

```
対象ログファイルを全て読み込む
以下のエントリを抽出:
- [PATTERN] エントリ（繰り返しテーマ）
- [ERROR] エントリ（ミスパターン）
- [INSIGHT] エントリ（価値ある洞察）
- [DECISION] エントリ（重要な意思決定）
```

**【Cognitive Memory: 睡眠とスキーマ生成の準備】**
- 各エントリの `Arousal` 値を評価し、Arousalの高い記憶断片を優先的に処理対象とする。
- 類似度の高いエントリ群（クラスタ）を特定する。

### Step 2: パターン統合（再固定化とスキーマ化）

**[PATTERN] の処理 (Schema Generation)**:
- 同一テーマのエントリ（完全部分グラフを形成する記憶クラスタ）をグルーピング
- 具体的なエピソードから抽象的なルール（スキーマ）を生成
- スキルレベルの知識として昇格候補を選定（出現3回以上）

**[ERROR] の処理 (Reconsolidation / Interference Forgetting)**:
- `memory/error-patterns.md` に EP-NNN フォーマットで追記
- 既存パターンとの重複チェック（重複なら出現回数を更新）
- **干渉忘却**: 新しい[ERROR]パターンによって古い仮説が完全に否定された場合、古い知識の重要度を意図的に下げる（または打ち消し線を引く）。

**[INSIGHT] の処理**:
- `memory/insights.md` に INS-NNN フォーマットで追記
- ドメインタグによりカテゴリ分類

### Step 3: スキル更新

対象ドメインスキルの `SKILL.md` を更新:
- 実績あるフレームワークを「Established」セクションへ
- 仮説レベルの知識は「Hypothesis」セクションへ
- アンチパターンは「Avoid」セクションへ

### Step 4: MEMORY.md 更新

`memory/MEMORY.md` を更新:
- 「確立された判断原則」セクションに新原則を追記
- 「Akiraの評価軸」を観察から更新
- 「繰り返すミスのパターン」のサマリーを更新
- 「活性化されたスキル」の状態を更新

### Step 5: Config 更新

`.nfd/config.json` を更新:
- `last_checkpoint`: 実行日時
- `checkpoint_count`: インクリメント
- `metrics.active_skills`: アクティブスキル数を更新

## 出力サマリー形式

結晶化完了後、以下のサマリーをAkiraに報告:

```
## Crystallization Checkpoint #N 完了

### 処理したログ
- 期間: YYYY-MM-DD 〜 YYYY-MM-DD（N日分）
- 総エントリ数: N件

### 更新内容
- error-patterns.md: +N件（合計N件）
- insights.md: +N件（合計N件）
- 更新スキル: [スキル名], [スキル名]
- MEMORY.md: N原則追加

### 主要な発見
1. [最重要パターン]
2. [次に重要なパターン]

### 次の結晶化予定
- 条件: [シグナル条件]
- 推定時期: [Week/Month]
```

## 注意事項

- ログの削除は行わない（ログは追記専用）
- 確信度の低い洞察は「Hypothesis」として明示
- 既存知識と矛盾する発見は古い知識に打ち消し線を引いて残す（削除しない）
