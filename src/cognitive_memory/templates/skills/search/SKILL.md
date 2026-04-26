---
name: search
description: Cognitive Memory cross-search. Search `memory/logs/` semantically via cogmem to surface past similar entries. Use when the user wants to consciously look up past records — phrases like "search past logs", "find logs for X", "have I done this before?", "did we discuss X before", "previous decision on X", "earlier session about X". Also auto-invoked by Session Init's flashback detection.
user-invocable: true
---

# SKILL: /search — Cognitive Memory Cross-Search

**Trigger**: `/search [keyword]` or Session Init's automatic flashback detection
**Time**: 30s–1min
**Purpose**: Cross-search `memory/logs/` to surface past similar entries

---

## Steps

### Step 1: Parse the query

- `/search [keyword]` → use the keyword directly
- Auto-invoked from Session Init → extract 3–5 keywords from current conversation context

### Step 2: Run semantic search

```bash
cogmem search "[keyword]" --json
```

This single command handles:
1. **Adaptive gate**: skips short greetings / slash commands
2. **Semantic search**: Ollama (multilingual-e5-large) + SQLite cosine similarity
3. **Keyword search**: Python in-process Grep equivalent
4. **Merge & dedupe**: semantic-first, content-based dedupe
5. **Scoring**: `(0.7 * cosine_sim + 0.3 * arousal) * time_decay`
6. **Fail-open**: continues on Ollama failure (Grep-only)

**Output JSON**:
```json
{
  "results": [
    {"score": 0.78, "date": "2026-03-15", "content": "...", "arousal": 0.8, "source": "semantic"}
  ],
  "status": "ok"
}
```

`status` values:
- `"ok"` — normal (semantic + Grep)
- `"degraded (ollama_unavailable)"` — Ollama down, Grep only
- `"degraded (no_index)"` — index not built, Grep only
- `"skipped_by_gate"` — adaptive gate skipped

### Step 3: Surface flashbacks

If any result has `score >= 0.75` and `arousal >= 0.6`:

```
💭 Flashback: on [date], we talked about "[excerpt]". Related to what's happening now?
```

### Step 4: Present results

Show hit count and top 3 results. If zero hits, say "no matches" plainly.

---

## Index management

### Build / refresh

```bash
cogmem index --all    # full reindex
cogmem index          # incremental (mtime diff)
```

Session Init runs incremental index automatically.

### Index stats

```bash
cogmem status
```

### Index location

`memory/vectors.db` (SQLite, gitignored)

### When index is corrupted

```bash
rm memory/vectors.db && cogmem index --all
```

The Markdown logs are the primary source of truth — the index is always rebuildable.

---

## Output format

```markdown
## /search results: "[keyword]"

**Hits**: N / 32 entries searched (status: ok)

| Date | Tag | Arousal | Score | Excerpt |
|------|-----|---------|-------|---------|
| 2026-03-15 | [INSIGHT] | 0.9 | 0.80 | ... |
| 2026-03-21 | [DECISION] | 0.7 | 0.76 | ... |

💭 Flashback candidate: [highest-relevance entry]
```

---

## `/search` vs `cogmem context-search`

| | `/search [keyword]` | `cogmem context-search` |
|---|---|---|
| Trigger | Manual (user invokes explicitly) | Auto (Contextual Search Protocol) |
| Result display | Full results table (top 5) | Flashback-passing only (top 3) |
| Filter | None (show all) | sim ≥ 0.65 and arousal ≥ 0.5 |
| Rate limit | None | 3 per session |
| Use case | Conscious lookup of past records | Auto-surface relevant memory mid-conversation |

## Auto-invocation

- **Session Init (Step 5)**: `/search` for initial flashback search
- **Mid-conversation (Contextual Search Protocol)**: `cogmem context-search` on topic shift

## Manual invocation scenarios

- User says "did we talk about this before?"
- A `[PATTERN]` tag appears for the 2nd+ time
- Starting discussion on a new theme — want to confirm past context
- User asks "search past logs", "find earlier session on X", "have we done this before?"
