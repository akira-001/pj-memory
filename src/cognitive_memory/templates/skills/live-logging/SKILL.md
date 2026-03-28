---
name: live-logging
description: Protocol for immediately appending to memory logs at important moments. Detailed entry format, Arousal gating, and déjà vu check steps.
user-invocable: false
---

# SKILL: Live Logging

**Purpose**: Record important moments immediately in `memory/logs/YYYY-MM-DD.md`
**Rule**: File operations happen in the **same turn** as the response (don't delay)

---

## Entry Format

```
### [Category] Title
*Arousal: [0.4-1.0] | Emotion: [Insight/Conflict/Surprise etc.]*
[Content — lines vary naturally with Arousal]

---
```

## Emotional Gating (Arousal determines detail level)

| Arousal | Lines | What's naturally included |
|---------|-------|--------------------------|
| 0.4-0.6 | 1-2 | Facts only (what happened/was decided) |
| 0.7-0.8 | 3-5 | + Causation, rationale, aliases |
| 0.9-1.0 | 5-10 | + Context, trial/error, user quotes, hypotheses |

High Arousal (0.8+) naturally includes by category:

| Category | Naturally included at high Arousal |
|----------|------------------------------------|
| [INSIGHT] | Previous assumption → new understanding, what triggered it |
| [ERROR] | Initial hypothesis, why it was wrong, how it was corrected |
| [DECISION] | Rejected options and reasons, deciding factor |
| [PATTERN] | Past occurrence count/dates, meaning of pattern |
| [QUESTION] | Context in which question arose, tentative hypothesis |
| [MILESTONE] | Aliases, related past decisions, path to completion |

## Log File Format

File: `memory/logs/YYYY-MM-DD.md` (date = session start date)
Generate header only on first creation. After that, just append to "## Log Entries".

```markdown
# YYYY-MM-DD Session Log

## Session Summary
[Written during wrap. Blank until then]

## Log Entries
[Entries appended via Live Logging]

---

## Handoff
[Written during wrap]
```

---

## Déjà Vu Check (before implementation/creation tasks)

Run before starting work when user requests implementation, creation, or fixes:

**Trigger phrases:**
- "create...", "implement...", "add...", "build..."
- "fix...", "update...", "change...", "modify..."
- "how does... work?", "is there...?"

**Steps:**
1. Run `cogmem search` with request keywords (include synonyms and old names)
2. Check for hits with `score >= 0.80` and `[MILESTONE]` or `[DECISION]` tags
3. If hits, judge relevance to current request:
   - **Exact match**: "Oh, I built that before. [Context]. It should be in [location]."
   - **Partial match**: "I built [related thing] before — is this different from that?"
   - **Unrelated**: Continue to normal flow
4. No hits → normal flow
