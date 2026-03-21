# TODOS

## Multi-tool template support (v0.3.0+)

**What:** `cogmem init --cursor` / `--cline` / `--windsurf` でツール別テンプレート生成
**Why:** 現在は Claude Code 専用。他の AI コーディングツール（Cursor の .cursorrules、Cline の .clinerules 等）向けにもテンプレートを生成することでユーザーベースを拡大
**Pros:** より広いユーザー層にリーチ
**Cons:** 各ツールの設定ファイル仕様の調査が必要、ツールのアップデートに追従するメンテコスト
**Depends on:** v0.2.0 の Claude Code 版が安定してから
**Context:** 各ツールの設定ファイル形式は異なるが、コアのルール（Session Init / Live Logging / Wrap / Crystallization）は同じ。CLAUDE.md テンプレートをベースに各ツール向けに変換する形になる。

## cogmem compact CLI (v0.3.0+)

**What:** `cogmem compact` でログ圧縮を CLI から実行
**Why:** 現在は Claude Code が直接 Wrap/Compact を実行するが、CLI 化すれば cron や CI/CD パイプラインからも自動実行可能になる
**Pros:** 自動化パイプラインでの利用、Claude Code セッション外からのメンテナンス
**Cons:** 高品質な compact には LLM が必要（ヘッダー行ベースの簡易版なら LLM なしで可能）。LLM 統合を入れるかどうかの設計判断が必要
**Depends on:** v0.2.0 が安定してから
**Context:** compact のコアロジックは「Arousal >= 0.6 のエントリを保持し、それ以外を省略」。これは LLM なしで実装可能。ただし「セッション概要」の生成は LLM が必要。2段階（フィルタリングのみ CLI / 概要生成は LLM 付き）で実装する選択肢もある。
