---
name: crystallize
description: Memory crystallization. Extracts knowledge from logs and integrates into skills and memory (NFD Algorithm 1). Auto-executed during wrap when signals fire.
user-invocable: true
---

# SKILL: /crystallize — Memory Crystallization

**Trigger**: Called from `wrap` when `cogmem signals` conditions are met, or manually via `/crystallize`
**Purpose**: Extract durable knowledge from logs and consolidate into summary and error patterns

---

## Steps

### Step 1: Scan logs (today + recent only — DO NOT read full history)

**Limit scope** (full-history Read is forbidden):
- Read today's log `memory/logs/YYYY-MM-DD.md`
- If multiple days have passed since last crystallization, also Read **up to 2 most recent days**
- Older logs MUST NOT be Read (they are already indexed by `cogmem index`; use `cogmem search` if needed)

Extract entries by category:
- `[PATTERN]` — recurring themes
- `[ERROR]` — judgment errors, broken assumptions
- `[INSIGHT]` — valuable realizations
- `[DECISION]` — important decisions

Prioritize high-Arousal memory fragments.

### Step 1.5: Duplicate check on existing files (tail / grep only — DO NOT full-read)

Goal: detect duplicates and get next sequence number. Past entries MUST NOT be fully Read:
- Read only the **last 30 lines** of `memory/error-patterns.md` → confirm latest EP-N number and recent pattern names
- Read only the **last 20 lines** of `memory/insights.md` → confirm latest INS-N number
- For potential duplicates, run `grep -n "<keyword>" memory/error-patterns.md` to inspect the relevant section only

This drastically reduces Read tokens during wrap (full history = hundreds of lines → tail of 30〜50 lines).

### Step 2: Pattern integration

**[PATTERN] processing:**
- Group entries on the same theme (3+ occurrences)
- Generate abstract rules (schemas) from concrete episodes
- Select candidates for promotion to skill-level knowledge

**[ERROR] processing:**
- Append to `memory/error-patterns.md` in EP-NNN format
- Check for duplicates with existing patterns (update count if duplicate)

### Step 3: Update memory/knowledge/summary.md

Add new principles to "Established Judgment Principles" section.
Update error pattern summary.

### Step 4: Record checkpoint

```bash
cogmem checkpoint
```

This automatically updates `last_checkpoint` and `checkpoint_count` in cogmem.toml.

### Step 5: Decay processing

```bash
cogmem decay
```

Applied automatically to consolidated logs:
- Arousal >= threshold → keep detail (vivid memory)
- recall_count >= threshold and recalled recently → keep
- recall_count >= threshold but not recalled recently → delete
- Otherwise → compress to compact, delete detail

### Step 6: Report to user

```
## Crystallization complete

**Logs processed**: N days (YYYY-MM-DD to YYYY-MM-DD)
**Entries**: N total
**Updates**:
  - error-patterns.md: +N entries (total N)
  - summary.md: N principles added
**Next checkpoint**: when conditions are met again
```

---

## Signal Conditions

| Condition | Threshold |
|-----------|-----------|
| Same-theme [PATTERN] entries | 3+ |
| Cumulative [ERROR] entries | 5+ |
| Log file days | 10+ |
| Days since last checkpoint | 21+ |

---

## Execution Timing

- **During Wrap**: Auto-execute if signal conditions are met (no confirmation needed)
- **During Session Init**: Notification only ("Will auto-execute during Wrap")
- **Manual**: `/crystallize` anytime
