---
name: session-init
description: Execute at session start. Prioritizes contexts/ briefing, runs cogmem index/signals, and notifies of flashbacks and signals.
user-invocable: false
---

# SKILL: Session Init

**Trigger**: Conversation starts (greeting, "let's begin", new topic)
**Purpose**: Restore context from previous session, check memory and signals

> identity/soul.md, knowledge/summary.md are already in context via @ references — do NOT Read them here.
> identity/user.md is the shared template. Per-user profile is loaded in Step 0.

---

## Step 0: Load per-user profile

Get `user_id` from `cogmem.local.toml` and load the per-user profile:

```bash
# Get user_id (cogmem.local.toml → cogmem.toml fallback)
grep -m1 'user_id' cogmem.local.toml 2>/dev/null || grep -m1 'user_id' cogmem.toml 2>/dev/null
```

- `user_id` found → Read `identity/users/{user_id}.md`
- File does not exist → skip (@identity/user.md serves as fallback)
- `user_id` empty or not set → skip

## Step 1: Check latest contexts briefing

```bash
ls -t memory/contexts/*.md | grep -v .gitkeep | head -1
```

- **File exists and is within 2 days** → Read to restore context → skip Step 2
- **Not found / too old** → proceed to Step 2 (fallback)

## Step 2: Read handoff section only (fallback)

*Skip if Step 1 found a contexts file*

```bash
ls -t memory/logs/*.md | head -2
```

Target: latest 1 log file only (prefer `.compact.md`).
Read only the "## Handoff" section (last ~40 lines), not the full file:
```
Read: <file-path>  offset=-40 lines
```

**[Delayed Wrap Detection]** If "## Handoff" is empty or missing (= wrap not executed):
1. Read full log and generate session summary (1-2 lines)
2. Write "## Session Summary"
3. Generate and write "## Handoff"
4. Generate `memory/contexts/YYYY-MM-DD.md` (same as wrap skill Step 2.5)
※ Skip today's log (current session)

## Step 3: Run cogmem index

```bash
cogmem index
```
- Skip if Ollama is not running
- If cogmem not installed: `pip install cogmem-agent`

## Step 4: Parallel execution (after Step 3)

Run these 2 **in parallel**:

```bash
# 1. Crystallization signal check
cogmem signals

# 2. Keyword search (only if conversation has specific topics)
cogmem search "<keywords from current context>"
```

**cogmem search condition**: Skip if the conversation only has generic phrases like "resume" or "hello". Run only when specific project names, technologies, or task names are present.

### Flashback detection
- Entries with `score >= 0.75` and `arousal >= 0.6` → present as flashback
- Speak naturally as if recalling (don't report date/score mechanically):
  "We talked about [content] before — this seems related to the current topic."
- Even fading logs can resurface if context similarity and Arousal are high

### Signals
- Notify only if conditions are met (wait until Wrap to execute)

> **Note**: `cogmem skills audit` is NOT run in Init — moved to Wrap Step 3.

## Step 5: Token budget check

Target: 6k tokens total. Recommend `/compact` if exceeded.

---

## Response Format

Add to the beginning only if notifications exist:

```
⚠️ Crystallization signal detected: [condition] (if applicable)
💭 Flashback: [past entry excerpt] (if applicable)
📊 Token budget exceeded: [recommended action] (if exceeded)
---
[Normal response]
```
