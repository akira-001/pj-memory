# Agents — Behavior Rules

## Auto-Execution Rules

Execute Session Init immediately after loading this file.
Do not wait for user instructions. Always execute on the first turn.
→ **Read the `session-init` skill and follow its steps**

Append to logs immediately at important moments (don't delay).
→ **Read the `live-logging` skill and follow its format**

Track and learn from every skill usage.
→ **Read the `skill-tracking` skill and follow its steps**

### Parallel Execution Principle

Run independent cogmem commands and tasks **in parallel**:
- Session Init: after index completes, run search / signals / audit in parallel
- During skill execution: track events run in background
- After task completion: learn runs in background
- Wrap: signals + track-summary run in parallel
- Implementation: independent file changes via subagents in parallel

---

## Phase → Skill Mapping

| Phase | Trigger | Skill to read |
|-------|---------|--------------|
| Session Init | Conversation starts (greeting, new topic) | `session-init` |
| Live Logging | Trigger table conditions below | `live-logging` |
| Skill Tracking | Any skill usage | `skill-tracking` |
| Wrap | Trigger phrases below | `wrap` |
| Crystallization | signals detected during Wrap | `crystallize` |

---

## Live Logging Triggers (always reference)

| Trigger | Tag | Arousal |
|---------|-----|---------|
| Direction change ("wait", "but actually") | [ERROR] | 0.7-0.9 |
| Same theme reappears (2nd+ time) | [PATTERN] | 0.7 |
| Moment of clarity ("I see", "aha") | [INSIGHT] | 0.8 |
| Rejection/cancellation decision | [DECISION] | 0.6-0.7 |
| Unresolved question emerges | [QUESTION] | 0.4 |
| Important task/phase completed | [MILESTONE] | 0.6 |

For entry format, Arousal gating, and déjà vu check → read the `live-logging` skill

---

## Name Resolution Order

1. If `identity/users/{user_id}.md` contains an "Agent name" entry → use that name
2. Otherwise use the name defined in `identity/soul.md`

---

## Wrap Trigger Phrases (always reference)

"thanks", "done for today", "see you tomorrow", "that's all",
"OK", or equivalent expressions in any language.

For detailed Wrap steps (retroactive check, skill improvement, identity update) → read the `wrap` skill
