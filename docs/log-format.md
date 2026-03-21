# Log Format Specification

Cognitive Memory parses structured markdown log files to build a searchable memory index.

## File Naming

```
memory/logs/YYYY-MM-DD.md
```

Files must start with a date pattern (`YYYY-MM-DD`). Files without this pattern are ignored.
Files ending in `.compact.md` are excluded from indexing (they are compressed summaries).

## File Structure

```markdown
# YYYY-MM-DD Session Log

## Session Summary
[Optional summary, not indexed]

## Log Entries

### [CATEGORY][DOMAIN] Entry Title
*Arousal: 0.7 | Emotion: Insight*
Entry content here. Must be at least 20 characters to pass noise filter.

---

### [CATEGORY][DOMAIN] Another Entry
*Arousal: 0.5 | Emotion: Determination*
More content here.

---

## 引き継ぎ
[Everything below this delimiter is excluded from indexing]
```

## Category Tags

| Tag | Usage |
|-----|-------|
| `[INSIGHT]` | New understanding, perspective shift |
| `[DECISION]` | Decision and its rationale |
| `[ERROR]` | Mistakes, failed assumptions, course corrections |
| `[PATTERN]` | Recurring themes, behaviors, thought patterns |
| `[QUESTION]` | Open questions, areas needing investigation |
| `[MILESTONE]` | Important achievements, phase transitions |

## Domain Tags

Combine with category tags: `[INSIGHT][TECH]`, `[DECISION][MARKET]`

Available: `[PROBLEM]` `[USER-RESEARCH]` `[MARKET]` `[CONCEPT]` `[BUSINESS-MODEL]` `[MVP]` `[TECH]` `[STRATEGY]` `[RISK]`

## Arousal

The `*Arousal: X.X | Emotion: ...*` line is optional but recommended.

- **Range**: 0.0 to 1.0
- **Default**: 0.5 (when not specified)
- **Effect**: Higher arousal → slower forgetting (adaptive half-life), higher search score

| Arousal | Meaning | Half-life (base=60d) |
|---------|---------|---------------------|
| 0.0 | Routine | 60 days |
| 0.5 | Notable | 90 days |
| 0.8 | Important | 108 days |
| 1.0 | Critical | 120 days |

## Noise Filter

Entries are excluded if:
- Content is shorter than 20 characters
- Content matches noise patterns (greetings, acknowledgments)

## Handover Delimiter

Default: `## 引き継ぎ`

Configurable in `cogmem.toml`:
```toml
[cogmem]
handover_delimiter = "## Handover"
```

Everything after this delimiter is excluded from indexing.
