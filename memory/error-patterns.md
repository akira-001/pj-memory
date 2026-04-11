# Error Patterns

## EP-001: subprocess.run の encoding 未指定 (Windows)
- **初回**: 2026-04-04
- **出現回数**: 1
- **パターン**: `subprocess.run(text=True)` で `encoding` を指定しないと、Windows の cp932 環境で UTF-8 出力のデコードに失敗する。`stdout` が None になり後続の文字列操作で TypeError。
- **対策**: 全ての `subprocess.run(text=True)` に `encoding="utf-8", errors="replace"` を追加。`stdout` の None ガードも入れる。
- **ドメイン**: cross-platform, subprocess

## EP-002: テストのハードコード日付（時間経過で境界越え）
- **初回**: 2026-04-11
- **出現回数**: 1
- **パターン**: `last_checkpoint="2026-03-20"` のようにハードコードした日付を使うと、実行日との差分が条件閾値（例: `checkpoint_interval_days=21`）を超えた時点でテストが突然失敗する。特に「N日以内」「N日経過」条件のテストで発生。
- **対策**: 相対的な日付は `date.today().isoformat()` や `(date.today() - timedelta(days=N)).isoformat()` で動的に生成する。
- **ドメイン**: testing, time-dependent

## EP-003: Jinja2 sort(attribute) は dict.items() のタプル index に非対応
- **初回**: 2026-04-11
- **出現回数**: 1
- **パターン**: Jinja2 テンプレートで `dict.items()|sort(attribute='1', reverse=True)` は動作しない。Jinja2 の `attribute` は `getattr()` ベースのため、タプルの数値 index は解決できない。結果が無ソートのまま出力される。
- **対策**: Python 側で `sorted(d.items(), key=lambda x: x[1], reverse=True)` してから dict で渡す。テンプレートには完成品を渡す設計にする。
- **ドメイン**: jinja2, template, testing
