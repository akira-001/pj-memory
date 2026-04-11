# MEMORY.md — cogmem-agent 結晶化済み知識

## 確立された判断原則
- subprocess.run(text=True) には必ず encoding="utf-8", errors="replace" を指定する（Windows 互換）
- ダッシュボード UI 変更はデザイン確定→実装の順序を守る（手戻り防止）
- テストの日付・時刻は動的生成（`date.today()`）、ハードコード禁止（時間経過で境界越え発生）
- モック対象はテスト対象モジュール内の実際の名前空間を使う（公開 API でなく内部関数）
- Jinja2 へはソート済みデータを渡す（テンプレート内の `sort(attribute=N)` は tuple index 非対応）
- Claude Code にないフックイベントは「何がそれを引き起こすか」から代替設計する

## 繰り返すミスのパターン
- EP-001: subprocess encoding 未指定（cross-platform）→ [error-patterns.md](error-patterns.md)
- EP-002: テストのハードコード日付（time-dependent）→ [error-patterns.md](error-patterns.md)
- EP-003: Jinja2 sort(attribute) の tuple index 非対応（template）→ [error-patterns.md](error-patterns.md)

## 活性化されたスキル
- cogmem-release: PyPI リリースワークフロー（0.20.6, 0.21.0, 0.23.0 で使用）

## 参照
- [error-patterns.md](error-patterns.md) — エラーパターン集
- [insights.md](insights.md) — 洞察集
