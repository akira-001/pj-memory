---
name: skill-tracking
description: Tracking and learning protocol for skill usage. Detailed steps for skill_start/end/deviation event logging, cogmem track, Skill Feedback, and Identity Auto-Update.
user-invocable: false
---

# SKILL: Skill Tracking & Feedback

---

## Skill Usage Start

When you begin following a SKILL.md, record in both the log and DB:

**Log:**
```
### [SKILL] <skill-name> started
*Arousal: 0.4 | Emotion: Execution*
[Task summary (1 line)]

---
```

**DB:**
```bash
cogmem skills track "<skill-name>" --event skill_start --description "<task summary>"
```

## Skill Usage Complete

**Log:**
```
### [SKILL] <skill-name> completed
*Arousal: 0.4 | Emotion: Completion*
track events: N (extra_step: X, skipped_step: Y, error_recovery: Z, user_correction: W)
→ Smooth execution / Improvements needed

---
```

**DB:**
```bash
cogmem skills track "<skill-name>" --event skill_end --description "<result summary>"
```

## Deviation Events (real-time)

Record immediately when deviating from skill steps (same turn as response):

| Situation | event_type |
|-----------|------------|
| Executed a step not in the skill | extra_step |
| Intentionally skipped a step | skipped_step |
| Error occurred and recovered | error_recovery |
| User gave a correction | user_correction |

```bash
cogmem skills track "<skill-name>" \
  --event <event_type> \
  --description "<brief description>" \
  [--step "<Step N>"]
```

**Parallel execution rules:**
- Deviation events: can run in background parallel to main task
- skill_start / skill_end: synchronous (flow markers)
- cogmem skills learn (after task): can run in background

**When NOT to record:** Smooth execution → no deviation events (only skill_start/end)

---

## Skill Feedback (after task completion)

After completing work that referenced a skill:

```bash
cogmem skills learn --context "<task summary>" --outcome "<result summary>" --effectiveness 0.0-1.0
```

### Creating/Improving Skills
- Create/edit directly in `.claude/skills/` (YAML frontmatter `description` required)
- Use `superpowers:writing-skills` if available for TDD flow

### Ingesting eval results
```bash
cogmem skills ingest --benchmark <workspace-path> --skill-name <skill-name>
```

### Auto-generating new skills
When the same type of task is repeated 3+ times, extract the pattern and create a new skill in `.claude/skills/`.

---

## Identity Auto-Update

### identity/user.md — auto-update (batch during Wrap)
Update when learning new info about the user:
- Expertise/skills identified during session
- Communication preferences observed
- Decision-making patterns, thinking style
- Basic info (name, role, timezone)

```bash
cogmem identity update --target user --json '{"section": "content"}'
```

Overwrite if new info conflicts with existing content.

### identity/soul.md — auto-update
Update when user gives feedback about agent behavior:
- Tone/speaking style change requests
- Role additions or changes
- Communication style changes

```bash
cogmem identity update --target soul --section "section" --content "content"
```
