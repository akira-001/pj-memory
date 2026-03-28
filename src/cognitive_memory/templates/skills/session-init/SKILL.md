---
name: session-init
description: Execute at session start. Reads context files, runs cogmem index/search/signals/audit in parallel, and notifies of flashbacks and signals.
user-invocable: false
---

# SKILL: Session Init

**Trigger**: Conversation starts (greeting, "let's begin", new topic)
**Purpose**: Restore context from previous session, check memory and signals

> identity/soul.md, identity/user.md, knowledge/summary.md are
> already in context via @ references — do NOT Read them here.

---

## Step 1: Check today's context file

```
Read: memory/contexts/YYYY-MM-DD.md (today's date)
```
- If exists: Read → understand user's current state, tasks, mood
- If not exists: skip

## Step 2: Read the 2 most recent log files

```bash
ls -t memory/logs/*.md | head -3
```
- Prefer `.compact.md` if it exists for a file
- Otherwise read the regular `.md`

**[Delayed Wrap Detection]** After reading, if "## Handoff" is empty or missing (= wrap not executed):
1. Scan all log entries and generate session summary (1-2 lines)
2. Write "## Session Summary"
3. Generate and write "## Handoff"
※ Skip today's log (current session)

## Step 3: Run cogmem index

```bash
cogmem index
```
- Skip if Ollama is not running
- If cogmem not installed: `pip install cogmem-agent`

## Step 4-5.5: Parallel execution (after Step 3)

Run these 3 **in parallel**:

```bash
# 1. Keyword search (flashback detection)
cogmem search "<keywords from current context>"

# 2. Crystallization signal check
cogmem signals

# 3. Skill audit
cogmem skills audit --json --brief
```

### Flashback detection
- Entries with `score >= 0.75` and `arousal >= 0.6` → present as flashback
- Speak naturally as if recalling (don't report date/score mechanically):
  "We talked about [content] before — this seems related to the current topic."
- Even fading logs can resurface if context similarity and Arousal are high

### Signals
- Notify only if conditions are met (wait until Wrap to execute)

### Audit
- Add notification if `recommendations` exist

## Step 6: Token budget check

Target: 6k tokens total. Recommend `/compact` if exceeded.

---

## Response Format

Add to the beginning only if notifications exist:

```
⚠️ Crystallization signal detected: [condition] (if applicable)
💭 Flashback: [past entry excerpt] (if applicable)
🔧 Skill audit: [recommendation] (if applicable)
📊 Token budget exceeded: [recommended action] (if exceeded)
---
[Normal response]
```
