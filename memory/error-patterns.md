# Error Patterns

## EP-001: subprocess.run の encoding 未指定 (Windows)
- **初回**: 2026-04-04
- **出現回数**: 1
- **パターン**: `subprocess.run(text=True)` で `encoding` を指定しないと、Windows の cp932 環境で UTF-8 出力のデコードに失敗する。`stdout` が None になり後続の文字列操作で TypeError。
- **対策**: 全ての `subprocess.run(text=True)` に `encoding="utf-8", errors="replace"` を追加。`stdout` の None ガードも入れる。
- **ドメイン**: cross-platform, subprocess
