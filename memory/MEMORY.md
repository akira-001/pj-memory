# MEMORY.md — cogmem-agent 結晶化済み知識

## 確立された判断原則
- subprocess.run(text=True) には必ず encoding="utf-8", errors="replace" を指定する（Windows 互換）
- ダッシュボード UI 変更はデザイン確定→実装の順序を守る（手戻り防止）

## 繰り返すミスのパターン
- EP-001: subprocess encoding 未指定（cross-platform）→ [error-patterns.md](error-patterns.md)

## 活性化されたスキル
- cogmem-release: PyPI リリースワークフロー（0.20.6, 0.21.0 で使用）

## 参照
- [error-patterns.md](error-patterns.md) — エラーパターン集
- [insights.md](insights.md) — 洞察集
