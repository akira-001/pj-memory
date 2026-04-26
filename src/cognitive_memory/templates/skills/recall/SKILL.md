---
name: recall
description: Cross-source recall. Search past work records, project info, and conversation context across `memory/logs/` (cogmem semantic + grep) and Claude Code's auto-memory (`~/.claude/projects/<project>/memory/*.md`). Use when the user needs past context — "search past logs", "find logs for X", "I forgot", "where was that?", "I think I did this before", "check the work log", "look up the previous session", "find what we decided about X". Also use when `/search` (cogmem-only) didn't find enough.
user-invocable: true
---

# SKILL: /recall — Cross-Source Past-Record Search

**Purpose**: Cross-search every memory source to restore past context.

While `/search` only searches cogmem's semantic index, `/recall` searches three sources. Project paths, configs, URLs, and other structured info often live in auto-memory; implementation details and handoffs often live in non-indexed parts of logs. The value of this skill is covering what cogmem's semantic search alone misses.

---

## Steps

### Step 1: Extract keywords

- `/recall [keyword]` → use directly
- Auto-trigger → identify "what is unknown" from the conversation, extract 3–5 keywords

### Step 2: Search auto-memory first (fast, high-precision)

Auto-memory is a treasure trove of structured info: project configs, paths, URLs, procedures. Check it first.

```
Grep tool:
  pattern: [keyword1|keyword2|keyword3]
  path: ~/.claude/projects/<auto-detected-project>/memory/
  output_mode: content
  context: 3
```

Include `MEMORY.md` (the index) in the search. Read full files when they hit.

**Early return**: if auto-memory yields a clear answer (URL, path, config value, procedure), skip Step 3–4 and answer directly. This saves significant tokens and response time.

### Step 3: Direct grep on `memory/logs/`

cogmem's semantic search only indexes log entries (blocks starting with `###`). Sections like "## Implementation notes" or "## Handoff" are not indexed, so direct grep is needed.

```
Grep tool:
  pattern: [keyword1|keyword2|keyword3]
  path: memory/logs/
  output_mode: content
  context: 5
```

If hits, Read the relevant section for full detail.

### Step 4: cogmem semantic search (supplement)

Run only if Step 2–3 didn't yield enough.

```bash
cogmem search "[keyword]" --json
```

Surface decisions / insights that don't match by keyword but are semantically related.

### Step 5: Merge & answer

Merge results in this priority:

1. **auto-memory hits** — structured info (paths, URLs, configs) — directly usable
2. **log grep hits** — implementation details, handoffs, summaries
3. **cogmem high-score hits** (score ≥ 0.75) — decisions, insights

Output:

```markdown
## /recall results: "[keyword]"

### auto-memory
- **[file]**: [excerpt]

### logs
- **[date]**: [excerpt]

### Answer
[Integrated answer. If nothing found, say so.]
```

For simple questions or low-hit results, skip the table/section formatting and answer concisely.

## Style rules

- Answer naturally, as if remembering
- Avoid system-flavored phrasing ("I'll search", "checking history", "let me look up")
- Always search before saying "I don't know"

---

## Auto-trigger conditions

Run this skill without asking when:

- File paths or project locations are unknown
- "Earlier" / "previously" / "before" — prior work details are needed
- Config values, URLs, token storage location are unclear
- `/search` (cogmem) returned nothing or insufficient
- User says "check past logs", "find logs for X", "look at the memory", "find the previous session"

## `/search` vs `/recall`

| | `/search` | `/recall` |
|---|---|---|
| Sources | cogmem (memory/logs/ entries only) | auto-memory + full log + cogmem |
| Best for | Insights / decisions / patterns | Project configs, paths, URLs, impl details |
| Use case | Reflect on past discussions / thoughts | Look up specific info, restore context |
| Speed | Fast (single cogmem call) | Stepwise with early return |
