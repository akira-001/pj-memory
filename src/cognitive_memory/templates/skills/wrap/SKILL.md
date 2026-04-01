---
name: wrap
description: Session close. Write summary and handoff to log, update MEMORY.md, commit & push.
user-invocable: true
---

# SKILL: /wrap — Session Close

**Trigger**: "thanks", "done for today", "see you tomorrow", "that's all", or equivalent

---

## Step 0: Retroactive check (run first)

```bash
cogmem watch --since "8 hours ago" --json --auto-suggest
```

Based on results:
- `fix_count >= 3` → append [PATTERN] entry to log (if not already recorded)
- `revert_count >= 1` → append [ERROR] entry to log (if not already recorded)
- `log_gap.has_gap == true` → notify user of logging gap
- `skill_signals` / `workflow_patterns` → auto-recorded as suggestions (via `--auto-suggest`)
- If any of the above: `cogmem watch --auto-log`

## Step 1: Write session summary

Write "## Session Summary" to today's log (`memory/logs/YYYY-MM-DD.md`) in 1-2 lines.

## Step 2: Generate handoff

Scan all log entries and generate "## Handoff":

```markdown
## Handoff
- **Continuing themes**: [unresolved questions, in-progress tasks]
- **Next actions**: [1-3 items in priority order]
- **Notes**: [risks, things to verify]
```

## Step 2.5: Generate contexts briefing file

Write `memory/contexts/YYYY-MM-DD.md` (today's date):

```markdown
# YYYY-MM-DD Session Briefing

## Summary
[1-sentence session summary (use content from Step 1)]

## Handoff
- Continuing themes: [1-2 items]
- Next actions: [up to 3 items, in priority order]
- Notes: [if any]

## Key decisions
- [Up to 3 DECISION / MILESTONE entries from today]
```

Keep under 20 lines. Write so the next Session Init can restore full context from this file alone.

## Step 3: Parallel execution

Run these 2 **in parallel**:
```bash
cogmem signals
cogmem skills track-summary --date YYYY-MM-DD --json
```

- If `signals` conditions are met → read `crystallize` skill and execute (no confirmation needed)
- Record "crystallization completed" in handoff if executed

## Step 3.5: Ingest skill-creator benchmarks

If skill-creator was used this session, ingest any pending benchmarks:
```bash
cogmem skills ingest --benchmark <workspace-path> --skill-name <skill-name>
```

## Step 3.7: Skill auto-improvement (follows `auto_improve` in cogmem.toml)

a. `auto_improve = "off"` → skip
b. No skills with `needs_improvement: true` → skip
c. `auto_improve = "ask"`: "[skill-name] has improvements needed (reason). Update?" → update approved only
d. For each skill to improve:
   - Read SKILL.md
   - Edit based on events (extra_step → add step, user_correction → highest priority)
   - **Immediately after Edit (atomic):**
     1. `cogmem skills resolve <skill-name>`
     2. `cogmem skills learn`
e. Record "Skill auto-improved: [skill-name] (reason)" in handoff

## Step 3.8: Skill creation candidate review (suggest-summary)

a. `auto_improve = "off"` → skip
b. Check suggestion clusters:
   ```bash
   cogmem skills suggest-summary --json
   ```
c. Empty result → skip
d. If candidates exist (2+ occurrences from `cogmem skills suggest` + `--auto-suggest`):
   - `"ask"`: Ask user "Create skill for [pattern] (Nx)?"
     - Approved → create skill, then promote:
       ```bash
       cogmem skills promote "[context]"
       ```
     - Rejected → dismiss to remove from future summaries:
       ```bash
       cogmem skills dismiss "[context]"
       ```
   - `"auto"`: Auto-create `.claude/skills/[name]/SKILL.md` → promote
   - YAML frontmatter (name, description) required for new skills
   - Record in handoff: "New skill created: [name] (suggest Nx)"

## Step 4: Update memory/knowledge/summary.md (if changes exist)

## Step 4.5: Identity update

```bash
cogmem identity detect --json
```

Scan session logs and extract:
- User info, expertise, communication preferences → `--target user`
- Agent behavior feedback → `--target soul`

```bash
cogmem identity update --target user --json '{"section": "content"}'
cogmem identity update --target soul --section "section" --content "content"
```

Skip if no relevant info found. Record "Identity updated: [user/soul] [section]" in handoff.

## Step 5: Increment total_sessions in cogmem.toml

## Step 6: Commit & push

```bash
git add -A
git commit -m "session: YYYY-MM-DD wrap

[session summary 1 line]

Co-Authored-By: Claude <noreply@anthropic.com>"
git pull --rebase origin main
git push origin main
```

If `git pull --rebase` fails with conflicts:
1. `git rebase --abort`
2. Report to user and ask for manual resolution (don't force-push or retry)

Report error to user on push failure; don't retry.

## Step 7: Completion report

```
## /wrap complete
**Today's session**: [summary 1 line]
**Entries logged**: [N / category breakdown]
**Next session**: [top priority action]
**Git**: committed & pushed
```

---

## Empty session (zero log entries)

Don't create a file. Just tell the user "nothing to record today."
