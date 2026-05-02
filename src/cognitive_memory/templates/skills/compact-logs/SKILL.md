---
name: compact-logs
description: Extract important entries from memory/logs/ and generate .compact.md files to reduce Session Init loading cost. This is distinct from Claude Code's native /compact (which compresses conversation history). Triggered by "/compact-logs", "compress logs", "compact memory logs".
user-invocable: true
---

# SKILL: /compact-logs — Log Compression

**Trigger**: `/compact-logs` or automatic (when log files exceed 10 days)
**Duration**: 5–10 minutes
**Purpose**: Extract important entries from raw logs, reducing Session Init loading cost

> NOTE: This skill compresses memory/logs/ files on disk.
> It is NOT the same as Claude Code's native `/compact` command, which compresses conversation history.

---

## Steps

### Step 1: Identify target files

```
Glob: memory/logs/*.md (excluding .compact.md)
```

Only files without a corresponding `.compact.md` are processed.
Files that already have `.compact.md` are skipped (re-compress with `/compact-logs --force`).

### Step 2: Filter important entries

**Retain entries that meet any of the following**:
- Arousal >= 0.6
- Category is `[INSIGHT]`, `[DECISION]`, or `[MILESTONE]`
- Listed in the handoff section

**Omit entries**:
- `[QUESTION]` with Arousal < 0.4 (resolved minor questions)
- Duplicate `[PATTERN]` entries (keep first occurrence, count the rest)
- `[ERROR]` entries already resolved by a `[DECISION]`

### Step 3: Generate .compact.md

```
Write: memory/logs/YYYY-MM-DD.compact.md
```

Format:

```markdown
# YYYY-MM-DD Compact Log
*Source: YYYY-MM-DD.md | Compression: N% | Generated: YYYY-MM-DD*

## Essence
[One-line session summary]

## Important Entries (Arousal >= 0.6)
[Filtered entries]

## Handoff
[Handoff section from source log]
```

### Step 4: Report completion

```
## /compact-logs complete

**Files processed**: N
**Compression ratio**: avg X% (entries: M → K)
**Session Init**: Will now prefer .compact.md on next load
```

---

## Integration with Session Init

In Session Init Step 2 (recent log loading):
1. `.compact.md` exists → load `.compact.md` (preferred)
2. `.compact.md` missing → load regular `.md`

Raw logs (`.md`) are never deleted — they remain available for `/search`.

---

## Auto-trigger condition

Checked at the same time as Session Init crystallization signals:

```
log_file_count >= 10  # 10 or more days of log files
```

If condition is met, add to Session Init response:

```
💡 /compact-logs recommended: Logs exceed 10 days. Run /compact-logs?
```

---

## Options

| Command | Behavior |
|---------|----------|
| `/compact-logs` | Process only uncompressed files |
| `/compact-logs --force` | Re-compress all files |
| `/compact-logs --preview` | Preview result without writing |
