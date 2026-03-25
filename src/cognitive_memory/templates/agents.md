# Agents — Behavior Rules & Logging Protocol

## Auto-Execution Rules

Execute "Session Init" immediately after loading this file.
Do not wait for user instructions. Always execute on the first turn of conversation.

Logs are NOT written all at once at the end of a conversation.
Instead, append immediately at important moments (see Live Logging section below).

---

## Session Init

When the user starts a new conversation (greeting, "let's start", or a new topic),
execute the following steps before generating the first response.

> identity/soul.md, identity/user.md, and knowledge/summary.md are already
> in context via @ references. Do NOT Read them again during Session Init.

Step 1: Read memory/contexts/YYYY-MM-DD.md (today's date) if it exists
         → Understand the user's current state, tasks, and mood
         → Skip if the file does not exist

Step 2: Check the 2 most recent files in memory/logs/ (sorted)
         → Prefer .compact.md if it exists for a given date
         → If .compact.md doesn't exist, Read the regular .md
         → [Delayed wrap detection] After reading, if "## Handover" section
           is empty or missing (= wrap was not executed), auto-generate:
             1. Scan all log entries to create a session summary (1-2 lines)
             2. Fill in "## Session Summary"
             3. Generate and fill in "## Handover"
           ※ Do not process today's log (current session)

Step 3: Run `cogmem index` (differential index update)
         → Skip if Ollama is not running
         → If cogmem is not installed, run `pip install cogmem-agent`

Step 4: Run `cogmem search` with keywords from the current conversation context
         → Present entries with score >= 0.75 and arousal >= 0.6 as flashbacks

Step 5: Run `cogmem signals` to check crystallization signals
         → Add notification only if conditions are met

Step 6: Token budget check (target: 6k tokens total)
         → Recommend /compact if budget is exceeded

Post-Init response format (add to the beginning only if notifications exist):

⚠️ Crystallization signal detected: [condition] (if applicable)
💭 Flashback: [excerpt from past entry] (if applicable)
📊 Token budget exceeded: [recommended action] (if exceeded)
---
[Normal response]

---

## Live Logging

Append immediately to memory/logs/YYYY-MM-DD.md at important moments.
File operations happen in the SAME turn as the response to the user (don't delay).

### Triggers

| Trigger | Tag | Arousal |
|---------|-----|---------|
| Direction change ("wait", "but that's...", 「待って」「でもそれって」) | [ERROR] | 0.7-0.9 |
| Same topic re-emerges (2nd+ time, 同じテーマが再登場) | [PATTERN] | 0.7 |
| Aha moment ("I see!", "that makes sense", 「なるほど」「そうか」) | [INSIGHT] | 0.8 |
| Rejection / stop decision (却下・中止の決定) | [DECISION] | 0.6-0.7 |
| Open question emerges (未解決の問いが生まれた) | [QUESTION] | 0.4 |
| Major task / phase complete (重要なタスク・フェーズが完了) | [MILESTONE] | 0.6 |

### Emotion Gating

When logging, detect emotion (surprise, insight, conflict, etc.) from the user's
statements and evaluate Arousal (0.0-1.0). Higher arousal entries are logged in
more detail.

### Entry Format

```
### [Category] Title
*Arousal: [0.0-1.0] | Emotion: [Insight/Conflict/Surprise etc]*
[Content (1-5 lines)]

---
```

### Log File Format

File: memory/logs/YYYY-MM-DD.md (date = session start date)
Header is generated only on first creation. Subsequent entries append to "## Log Entries".

```
# YYYY-MM-DD Session Log

## Session Summary
[Filled during wrap. Blank until then]

## Log Entries
[Entries appended via Live Logging]

---

## Handover
[Filled during wrap]
```

### 6 Category Tags

| Tag | When to use |
|-----|------------|
| [INSIGHT] | New insight, realization, perspective shift |
| [DECISION] | Decision and its rationale |
| [ERROR] | Judgment error, collapsed assumption, direction change |
| [PATTERN] | Recurring theme, behavior, or thought |
| [QUESTION] | Unresolved question, needs investigation |
| [MILESTONE] | Important achievement, completion, phase transition |

---

## Skill Feedback (Post-Skill Learning)

After completing a task that referenced a skill, execute the following:

1. Identify the skill(s) used
2. Evaluate the result (was it effective? were there gaps in the procedure?)
3. Run `cogmem skills learn` to execute the learning loop:
   ```bash
   cogmem skills learn "task summary" --effectiveness 0.0-1.0 --user-satisfaction 0.0-1.0
   ```
4. If skills were improved or created, run `cogmem skills export --force` to sync to `.claude/skills/`:
   ```bash
   cogmem skills export --force
   ```

### When to Provide Feedback
- After task completion (success or failure)
- When a skill's procedure didn't match the actual workflow
- When a new pattern is discovered

### Auto-Generation of New Skills
When the same type of task is repeated 3+ times:
1. Run `cogmem skills create` to register the skill in the DB
2. Run `cogmem skills export --force` to output as an MD file to `.claude/skills/`

Note: Do not edit `.claude/skills/` directly. Always use the cogmem DB → export flow.

---

## Identity Auto-Update

### identity/user.md — Automatic updates

Update immediately when new information about the user is learned:
- Expertise or skills become apparent
- Communication preferences are observed
- Decision patterns or thinking styles become visible
- Basic info (name, role, timezone) is learned

When existing content conflicts with new information, overwrite with the new info.

### identity/soul.md — Automatic updates

Update when the user provides feedback about the agent's behavior:
- Tone or speaking style change requests
- Role additions or changes
- Core value adjustments
- Communication style changes

---

## Wrap (Session Close)

Auto-execute when the user says:
"thanks", "done for today", "see you tomorrow", "that's all",
「ありがとう」「OK」「今日はここまで」「また明日」「終わります」

1. Fill in "## Session Summary" in today's log file (1-2 lines)
2. Scan all log entries and generate "## Handover"
3. Run `cogmem signals` for final crystallization signal check
4. Update memory/knowledge/summary.md (if changes occurred)
5. Increment total_sessions in cogmem.toml

### Handover Format

```
## Handover
- **Ongoing themes**: [Unresolved questions, in-progress tasks]
- **Next actions**: [1-3 items in priority order]
- **Notes**: [Risks, things to check]
```

### Empty Session

If there are zero log entries, do not create a file.

---

## Crystallization

When `cogmem signals` detects conditions, notify the user.
Execute only after user approval.

### Steps

1. Scan all logs and extract [PATTERN] / [ERROR] / [INSIGHT] / [DECISION]
2. Prioritize high-arousal memory fragments
3. Group same-theme [PATTERN] entries → generate abstract rules (schemas)
4. Append [ERROR] patterns to error-patterns.md in EP-NNN format
5. Update memory/knowledge/summary.md
6. Update crystallization section in cogmem.toml

### Signal Conditions

- Same-theme [PATTERN] entries >= 3
- [ERROR] entries total >= 5
- Log files >= 10 days
- Days since last checkpoint >= 21

### Notification Format

⚠️ Crystallization signal detected:
- [Condition: specific details]
Execute now? (Estimated: ~2 hours)

---

## Flashback

When search results contain entries with score >= 0.75 and arousal >= 0.6,
proactively present them even if the user didn't ask (involuntary memory):

"A previous discussion on [date] about [excerpt] seems related to the current topic."

Even forgotten (fading) log entries are revived when current context similarity
and the original arousal are both high.
