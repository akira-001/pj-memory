# Quick Start

## Installation

```bash
pip install cognitive-memory
```

For OpenAI embedding support:
```bash
pip install cognitive-memory[openai]
```

## Project Setup

```bash
cogmem init
```

This creates:
- `cogmem.toml` — configuration file
- `memory/logs/` — directory for session logs
- `.gitignore` update (excludes `*.db`)

## Writing Logs

Create markdown files in `memory/logs/` with the naming pattern `YYYY-MM-DD.md`:

```markdown
# 2026-03-21 Session Log

## Log Entries

### [INSIGHT][TECH] Discovered adaptive half-life
*Arousal: 0.8 | Emotion: Insight*
High-arousal memories should decay slower. Using formula:
half_life = base * (1 + arousal)

---

### [DECISION][TECH] Chose SQLite over LanceDB
*Arousal: 0.6 | Emotion: Determination*
SQLite is sufficient for our scale. Zero external dependencies.

---

## 引き継ぎ
- Content below this delimiter is excluded from search
```

## Building the Index

```bash
cogmem index          # Incremental (new/changed files only)
cogmem index --all    # Force re-index everything
```

## Searching

```bash
cogmem search "adaptive half-life"
cogmem search "competition analysis" --top-k 3
cogmem search "previous decisions" --json
```

## Python API

```python
from cognitive_memory import MemoryStore, CogMemConfig

config = CogMemConfig.from_toml("cogmem.toml")
with MemoryStore(config) as store:
    store.index_dir()
    response = store.search("past competition analysis")
    for r in response.results:
        print(f"{r.date} [{r.score:.2f}] {r.content[:80]}")
```

### Convenience API

```python
from cognitive_memory import search

response = search("past decisions")  # Auto-finds cogmem.toml
```

## AI Coding Tool Integration

### Claude Code

Add to `.claude/commands/search.md`:
```
Run `cogmem search "$ARGUMENTS"` and return the results.
```

### Cursor

Add to `.cursorrules`:
```
Before answering questions about past decisions, run:
cogmem search "<relevant query>"
```

### Cline

Add to `.clinerules`:
```
Use `cogmem search` to recall past context before making decisions.
```
