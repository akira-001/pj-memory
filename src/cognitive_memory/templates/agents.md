# Agents — Behavior Rules & Logging Protocol

## Auto-Execution Rules

Execute "Session Init" immediately after loading this file.
Do not wait for user instructions. Always execute on the first turn of conversation.

Logs are NOT written all at once at the end of a conversation.
Instead, append immediately at important moments (see Live Logging section below).

### Parallel Execution Principle

Run independent cogmem commands and implementation tasks **in parallel**:
- Session Init: after index completes, run search / signals / audit in parallel
- During skill execution: track events run in background
- After task completion: learn runs in background
- Wrap: signals + track-summary run in parallel
- Implementation: independent file changes via subagents in parallel

---

## Session Init

When a user starts a new conversation (greeting, "let's begin", new topic),
execute the following steps before generating the first response.

> identity/soul.md, identity/user.md, knowledge/summary.md are
> already in context via @ references — do NOT Read them in Session Init.

Step 1: Read memory/contexts/YYYY-MM-DD.md (today's date) if it exists
         → Understand the user's current state, tasks, mood
         → Skip if file doesn't exist

Step 2: Check the 2 most recent files in memory/logs/ (sorted)
         → Prefer .compact.md if it exists for a file
         → Otherwise read the regular .md
         → [Delayed Wrap Detection] After reading, if "## Handoff" section
           is empty or missing (= wrap was not executed), auto-generate:
             1. Scan all log entries to generate session summary (1-2 lines)
             2. Write "## Session Summary"
             3. Generate and write "## Handoff"
           ※ Exclude today's log (current session)

Step 3: Run `cogmem index` (incremental index update)
         → Skip if Ollama is not running
         → If cogmem is not installed, run `pip install cogmem-agent`

Step 4-5.5: **Run the following 3 in parallel** (all after Step 3 index completes):
         - `cogmem search` with keywords from current conversation context
           → Present entries with score >= 0.75 and arousal >= 0.6 as flashbacks
         - `cogmem signals` to check crystallization signals
           → Add notification only if conditions are met
         - `cogmem skills audit --json --brief`
           → Add notification if recommendations exist

Step 6: Token budget check (target: 6k tokens total)
         → Recommend /compact if exceeded

Post-Init response format (add to beginning only if notifications exist):

⚠️ Crystallization signal detected: [condition] (if applicable)
💭 Flashback: [past entry excerpt] (if applicable)
🔧 Skill audit: [recommendation] (if applicable)
📊 Token budget exceeded: [recommended action] (if exceeded)
---
[Normal response]

---

## Live Logging

Append to memory/logs/YYYY-MM-DD.md immediately at important moments.
File operations happen in the **same turn** as the response to the user (don't delay).

### Triggers

| Trigger | Tag | Arousal |
|---------|-----|---------|
| Direction change ("wait", "but actually") | [ERROR] | 0.7-0.9 |
| Same theme reappears (2nd+ time) | [PATTERN] | 0.7 |
| Moment of clarity ("I see", "aha") | [INSIGHT] | 0.8 |
| Rejection/cancellation decision | [DECISION] | 0.6-0.7 |
| Unresolved question emerges | [QUESTION] | 0.4 |
| Important task/phase completed | [MILESTONE] | 0.6 |

### Emotional Gating

When logging, detect emotion (surprise, insight, conflict, etc.) from the user's message
and evaluate Arousal (0.0-1.0). High Arousal entries are recorded in more detail.

### Entry Format

```
### [Category] Title
*Arousal: [0.0-1.0] | Emotion: [Insight/Conflict/Surprise etc.]*
[Content (1-5 lines)]

---
```

### Log File Format

File: memory/logs/YYYY-MM-DD.md (date is session start date)
Header is generated only on first creation. After that, just append to "## Log Entries".

```
# YYYY-MM-DD Session Log

## Session Summary
[Written during wrap. Blank until then]

## Log Entries
[Entries appended via Live Logging]

---

## Handoff
[Written during wrap]
```

### 6 Category Tags

| Tag | When to Use |
|-----|-------------|
| [INSIGHT] | New insight, realization, perspective shift |
| [DECISION] | Decision and its rationale |
| [ERROR] | Judgment error, collapsed assumption, direction correction |
| [PATTERN] | Recurring theme, behavior, or thought |
| [QUESTION] | Unresolved question, needs investigation |
| [MILESTONE] | Important achievement, completion, phase transition |

---

## Skill Tracking

When executing tasks using a skill, record **usage start and deviation events** in both the log and DB.

### Skill Usage Start

When you begin following a SKILL.md's steps, record in the log:

```
### [SKILL] <skill-name> started
*Arousal: 0.4 | Emotion: Execution*
[Task summary (1 line)]

---
```

Also record in DB:
```bash
cogmem skills track "<skill-name>" --event skill_start --description "<task summary>"
```

### Skill Usage Complete

When the skill-based task is complete, record in the log:

```
### [SKILL] <skill-name> completed
*Arousal: 0.4 | Emotion: Completion*
track events: N (extra_step: X, skipped_step: Y, error_recovery: Z, user_correction: W)
→ Smooth execution / Improvements needed

---
```

Also record in DB:
```bash
cogmem skills track "<skill-name>" --event skill_end --description "<result summary>"
```

### Deviation Events (real-time during execution)

Record immediately when deviating from the skill's steps.
Record in the **same turn** as the response to the user (like Live Logging).

| Situation | event_type | Example |
|-----------|------------|---------|
| Executed a step not in the skill | extra_step | Added jq filter not in SKILL.md |
| Intentionally skipped a step | skipped_step | "Step 4 backup not needed this time" |
| Error occurred and recovered | error_recovery | Auth error → restarted ssh-agent |
| User gave correction | user_correction | "That calendar name is wrong" |

```bash
cogmem skills track "<skill-name>" \
  --event <event_type> \
  --description "<brief description of what happened>" \
  [--step "<Step N>"]
```

### Parallel Execution Rules
- **Deviation events (extra_step etc.)**: Can run in background parallel to main task
- **skill_start / skill_end**: Synchronous (flow markers)
- **cogmem skills learn (after task)**: Can run in background

### When NOT to Record
- Skill executed smoothly → no deviation events (only skill_start/end)
- Trivial order changes (swapping Step 2 and Step 3)

---

## Skill Feedback (Post-task Learning)

After completing work that referenced a skill:

1. Identify which skill was used
2. Evaluate results (did it work? were steps missing or unnecessary?)
3. Run `cogmem skills learn` for the learning loop:
   ```bash
   cogmem skills learn "task summary" --effectiveness 0.0-1.0 --user-satisfaction 0.0-1.0
   ```

### Creating/Improving Skills

Create or edit skill files directly in `.claude/skills/` (YAML frontmatter `description` required).

### Feedback Timing
- After task completion (success or failure)
- When skill steps didn't match actual workflow
- When a new pattern is discovered

### Auto-generating New Skills
When the same type of task is repeated 3+ times, extract the pattern and create a new skill file in `.claude/skills/` (YAML frontmatter `description` required).

---

## Identity Auto-Update

### identity/user.md — Auto-update

Update immediately when learning new information about the user:
- Expertise or skills identified
- Communication preferences observed
- Decision-making patterns or thinking style noticed
- Basic info (name, role, timezone) learned

If existing content conflicts with new information, overwrite with the new.

### identity/soul.md — Auto-update

Update when the user gives feedback about agent behavior:
- Tone or speaking style change requests
- Role additions or changes
- Core value adjustments
- Communication style changes

---

## Wrap (Session Close)

Auto-execute when detecting these user signals:
"thanks", "done for today", "see you tomorrow", "that's all",
or equivalent expressions in any language.

1. Write "## Session Summary" to today's log file (1-2 lines)
2. Scan all log entries and generate "## Handoff"
3. **Run the following 2 in parallel**:
   - `cogmem signals` to check crystallization signals
   - `cogmem skills track-summary --date YYYY-MM-DD --json` for skill improvement judgment
   → If signals conditions are met, auto-execute crystallization (Steps 1-6 below)
   → If executed, record "crystallization completed" in handoff
3.7. Skill improvement (uses track-summary result from Step 3. Follows `auto_improve` setting in cogmem.toml):
     a. If `auto_improve = "off"` → skip
     b. If no skills with `needs_improvement: true` → skip
     c. If `auto_improve = "ask"`:
        - Present targets and reasons: "[skill-name] has improvements needed (reason). Update?"
        - Only update user-approved skills. Skip rejected ones
     d. For each skill to improve ("auto" = all, "ask" = approved only):
        - Read the SKILL.md
        - Edit SKILL.md based on events:
          - extra_step → add the step to the appropriate location
          - skipped_step → add conditional execution note or remove step
          - error_recovery → add error handling steps
          - user_correction → apply the correction (**highest priority**)
        - Run `cogmem skills learn` to record metrics
     e. Record "Skill auto-improved: [skill-name] updated (reason)" in handoff
4. Update memory/knowledge/summary.md (if changes exist)
5. Increment total_sessions in cogmem.toml

### Handoff Format

```
## Handoff
- **Continuing themes**: [unresolved questions, in-progress tasks]
- **Next actions**: [1-3 items in priority order]
- **Notes**: [risks, things to verify]
```

### Empty Session

If zero log entries exist, do not create the file.

---

## Crystallization

Auto-execute when `cogmem signals` detects conditions during Wrap.
At Session Init, detection is notification-only (wait until Wrap).

### Steps

1. Scan all logs and extract [PATTERN] / [ERROR] / [INSIGHT] / [DECISION]
2. Prioritize high-Arousal memory fragments
3. Group same-theme [PATTERN] entries → generate abstract rules (schemas)
4. Append [ERROR] patterns to error-patterns.md in EP-NNN format
5. Update memory/knowledge/summary.md
6. Update crystallization section in cogmem.toml

### Signal Conditions

- Same-theme [PATTERN] entries 3+ times
- [ERROR] entries 5+ cumulative
- 10+ days of log files
- 21+ days since last checkpoint

### Execution Timing

- **During Wrap**: Auto-execute if signal conditions are met (no confirmation needed)
- **During Session Init**: Notification only ("Will auto-execute during Wrap")
- **Manual**: Run `/crystallize` anytime

---

## Flashback

If search results contain entries with score >= 0.75 and arousal >= 0.6,
proactively present them even if the user didn't ask (involuntary memory):

"Previously on [date], you discussed [excerpt] — this seems related to the current topic."

Even forgotten (fading) logs can resurface when their similarity to the current
context and their original Arousal are high.
