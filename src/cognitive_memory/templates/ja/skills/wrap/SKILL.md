---
name: wrap
description: セッション正式クローズ。ログに概要・引き継ぎを記入し、MEMORY.md更新、コミット&プッシュ
user-invocable: true
---

# SKILL: /wrap — セッションクローズ

**トリガー**: 「ありがとう」「OK」「今日はここまで」「また明日」「終わります」/ "thanks", "done for today", "see you tomorrow", "that's all"

---

## Step 0: 遡及チェック（最初に実行）

```bash
cogmem watch --since "8 hours ago" --json --auto-suggest
```

結果に基づいて:
- `fix_count >= 3` → [PATTERN] エントリをログに追記（まだ記録されていなければ）
- `revert_count >= 1` → [ERROR] エントリをログに追記（まだ記録されていなければ）
- `log_gap.has_gap == true` → ログ漏れ警告をユーザーに通知
- `skill_signals` / `workflow_patterns` → `--auto-suggest` で自動的に候補として記録済み
- 上記いずれかに該当した場合、`cogmem watch --auto-log` で自動追記

## Step 1: セッション概要を記入

本日のログファイル（`memory/logs/YYYY-MM-DD.md`）に「## セッション概要」を記入（1〜2行）。

## Step 2: 引き継ぎを生成

ログエントリ全体を走査し「## 引き継ぎ」を生成:

```markdown
## 引き継ぎ
- **継続テーマ**: [未解決の問い、進行中のタスク]
- **次のアクション**: [1〜3項目を優先度順に]
- **注意事項**: [リスク、確認すべきこと]
```

## Step 2.5: contexts ブリーフィングファイルを生成

`memory/contexts/YYYY-MM-DD.md`（本日の日付）を Write:

```markdown
# YYYY-MM-DD セッションブリーフィング

## サマリー
[セッション概要の1文（Step 1 の内容を使う）]

## 引き継ぎ
- 継続テーマ: [1〜2項目]
- 次のアクション: [最大3件、優先度順]
- 注意事項: [あれば]

## 主要決定
- [本日の DECISION / MILESTONE エントリから最大3件]
```

20行以内に収める。次回 Session Init がこのファイルだけでコンテキスト復元できるように記述する。

## Step 3: 並列実行

以下の2つを**並列**で実行する:
```bash
cogmem signals          # 記憶の定着シグナルチェック
cogmem skills track-summary --date YYYY-MM-DD --json  # スキル改善判定
```

- `signals` が条件を満たす場合 → `crystallize` スキルを読んで実行（確認不要）
- 実行した場合、引き継ぎに「記憶の定着実施済み」と記録

## Step 3.5: skill-creator benchmark 取り込み

本セッションで skill-creator を使用した場合、未取り込みの benchmark を自動取り込み:
```bash
cogmem skills ingest --benchmark <workspace-path> --skill-name <skill-name>
```

## Step 3.7: スキル自動改善（cogmem.toml の `auto_improve` 設定に従う）

a. `auto_improve = "off"` → スキップ
b. `track-summary` で `needs_improvement: true` のスキルがなければスキップ
c. `auto_improve = "ask"` の場合: 「[スキル名] に改善点あり（理由）。更新する？」→ 承認分のみ更新
d. 改善対象スキルごとに（"auto" は全件、"ask" は承認分のみ）:
   - SKILL.md を Read
   - events の内容に基づいて SKILL.md を Edit:
     - extra_step → 手順を追加
     - skipped_step → 条件付き実行の注記を追加 or 削除
     - error_recovery → エラーハンドリング手順を追加
     - user_correction → 指摘内容を反映（最優先）
   - **Edit 直後に必ず連続実行（アトミック）:**
     1. `cogmem skills resolve <skill-name>`
     2. `cogmem skills learn`
e. 引き継ぎに「スキル自動改善: [スキル名] 更新（理由）」と記録

## Step 3.8: スキル化候補のレビュー（suggest-summary）

a. `auto_improve = "off"` → スキップ
b. 候補を集計:
   ```bash
   cogmem skills suggest-summary --json
   ```
c. 結果が空なら → スキップ
d. 候補がある場合（2回以上の繰り返しパターン — `cogmem skills suggest` + `--auto-suggest` で蓄積）:
   - `"ask"`: 「[パターン名]（N回）をスキル化する？」とユーザーに確認
     - 承認 → スキル作成後に promote:
       ```bash
       cogmem skills promote "[context]"
       ```
     - 拒否 → dismiss で候補から除外:
       ```bash
       cogmem skills dismiss "[context]"
       ```
   - `"auto"`: 自動で `.claude/skills/[name]/SKILL.md` を作成 → promote
   - スキル作成時は YAML frontmatter（name, description）必須
   - 引き継ぎに「スキル新規作成: [名前]（suggest N回）」と記録

## Step 4: memory/knowledge/summary.md を更新（変化があれば）

## Step 4.5: Identity 更新

```bash
cogmem identity detect --json
```

本セッションのログを走査し、以下を抽出:
- ユーザーの基本情報・専門性・コミュニケーション好み・意思決定パターン → `--target user`
- エージェントの振る舞いへのフィードバック → `--target soul`

```bash
cogmem identity update --target user --json '{"セクション名": "内容"}'
cogmem identity update --target soul --section "セクション名" --content "内容"
```

該当情報がなければスキップ。引き継ぎに「Identity 更新: [user/soul] [更新セクション]」と記録。

## Step 5: cogmem.toml の total_sessions をインクリメント

## Step 6: 自動コミット & プッシュ

```bash
git add -A
git commit -m "session: YYYY-MM-DD wrap (Session N)

[セッション概要1行]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git pull --rebase origin main
git push origin main
```

`git pull --rebase` でコンフリクトが発生した場合:
1. `git rebase --abort` で中断
2. ユーザーに報告し、手動解決を依頼（force-push やリトライはしない）

push 失敗時はエラーをユーザーに伝え、手動対応を促す（リトライしない）。

## Step 7: 完了報告

```
## /wrap 完了
**今日のセッション**: [概要1行]
**記録したエントリ**: [N件 / カテゴリ内訳]
**次回への引き継ぎ**: [最優先アクション1件]
**Git**: コミット済み & プッシュ完了
```

---

## 空セッション（ログエントリがゼロ件）

ファイルを作成しない。「今日は記録なし」とAkiraに伝えるだけ。
