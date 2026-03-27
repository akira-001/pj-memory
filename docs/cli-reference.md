# cogmem CLI Reference

Complete reference for every `cogmem` command.

```
cogmem <command> [options]
```

---

## 1. Setup

### `cogmem init`

Scaffold a new cogmem project. Creates directory structure, config, identity templates, sample skill, and CLAUDE.md integration.

```
cogmem init [--dir DIR] [--lang LANG]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dir` | `.` | Target directory |
| `--lang` | *(interactive)* | Language for templates: `en` or `ja`. Prompts if omitted. |

**Created structure:**

```
<dir>/
  cogmem.toml
  CLAUDE.md                  # appended if exists
  .gitignore                 # updated with *.db
  identity/
    agents.md
    soul.md
    user.md
  memory/
    logs/.gitkeep
    knowledge/
      summary.md
      error-patterns.md
    contexts/.gitkeep
  .claude/skills/
    memory-recall.md
```

Also installs the Anthropic `skill-creator` plugin if Claude Code is available.

**Example:**

```bash
cogmem init --dir ./my-project --lang en
```

```
Created /path/to/my-project/cogmem.toml
Created /path/to/my-project/identity/agents.md
Created /path/to/my-project/identity/soul.md
Created /path/to/my-project/identity/user.md
Created /path/to/my-project/memory/logs/
Created /path/to/my-project/memory/knowledge/summary.md
Created /path/to/my-project/memory/knowledge/error-patterns.md
Created /path/to/my-project/memory/contexts/
Created /path/to/my-project/.claude/skills/memory-recall.md
Created /path/to/my-project/.claude/skills/

Setup complete! Next steps:
  1. Edit identity/soul.md to define your agent's personality
  2. Start Claude Code -- CLAUDE.md will be loaded automatically
  3. Your agent now has cognitive memory!
  4. Skills in .claude/skills/ will be auto-loaded by the agent
```

---

### `cogmem migrate`

Upgrade project files from older versions (e.g., rename `agent.md` to `soul.md`, update CLAUDE.md references).

```
cogmem migrate [--dir DIR]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dir` | `.` | Target directory |

**Example:**

```bash
cogmem migrate --dir ./my-project
```

```
Migration complete:
  - Renamed identity/agent.md -> identity/soul.md
  - Updated cogmem.toml: agent -> soul
  - Updated CLAUDE.md
```

If already up to date:

```
Nothing to migrate -- project is up to date.
```

---

## 2. Memory

### `cogmem index`

Build or update the memory index. Parses log files in `memory/logs/` and indexes entries into the SQLite database with optional vector embeddings.

```
cogmem index [--all] [--file FILE]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--all` | `false` | Force re-index all files (ignores change detection) |
| `--file` | *(none)* | Index a single specific file |

**Example:**

```bash
cogmem index
```

```
Done: 42 entries indexed in 1.3s
```

```bash
cogmem index --file 2026-03-26.md
```

```
Indexed 8 entries from 2026-03-26.md
```

---

### `cogmem search`

Search memories using keyword and/or semantic (vector) search.

```
cogmem search QUERY [--top-k N] [--json]
```

| Argument/Flag | Default | Description |
|---------------|---------|-------------|
| `QUERY` | *(required)* | Search query string |
| `--top-k` | `5` | Number of results to return |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem search "skill tracking"
```

```
Status: ok
Results: 3

--- [1] score=0.87 date=2026-03-25 arousal=0.7 source=2026-03-25.md ---
  ### [DECISION] Skill tracking protocol
  Decided to track skill usage with cogmem skills track...

--- [2] score=0.72 date=2026-03-24 arousal=0.6 source=2026-03-24.md ---
  ### [MILESTONE] Skill system v2
  ...
```

**JSON output** (`--json`):

```json
{
  "results": [
    {
      "content": "### [DECISION] Skill tracking protocol\n...",
      "score": 0.87,
      "date": "2026-03-25",
      "arousal": 0.7,
      "source": "2026-03-25.md",
      "category": "DECISION"
    }
  ],
  "status": "ok"
}
```

---

### `cogmem context-search`

Context-aware memory search. Applies a relevance gate using session keywords, filtering results that are topically related to the current conversation.

```
cogmem context-search QUERY [--top-k N] [--json] [--keywords WORD ...]
```

| Argument/Flag | Default | Description |
|---------------|---------|-------------|
| `QUERY` | *(required)* | Search query string |
| `--top-k` | `3` | Number of results to return |
| `--json` | `false` | Output as JSON |
| `--keywords` | *(none)* | Session keywords for the relevance gate |

**Example:**

```bash
cogmem context-search "error handling" --keywords deploy CI --top-k 5
```

Output format is identical to `cogmem search`.

---

### `cogmem status`

Show index statistics: number of indexed files, total entries, and database size.

```
cogmem status
```

No flags.

**Example:**

```bash
cogmem status
```

```
Indexed files: 12
Total entries: 156
Database size: 284.3 KB
```

---

### `cogmem recall-stats`

Show the most frequently recalled memories, ranked by recall count.

```
cogmem recall-stats [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem recall-stats
```

```
 Recalls  Arousal        Date  Title
----------------------------------------------------------------------
       5     0.80  2026-03-20  ### [INSIGHT] Vivid encoding principle
       3     0.70  2026-03-18  ### [DECISION] Three-layer skill arch
       2     0.90  2026-03-15  ### [ERROR] Shallow search false negat
```

---

## 3. Monitoring

### `cogmem signals`

Check crystallization signals. Evaluates whether accumulated logs meet conditions for memory consolidation (e.g., 3+ PATTERN entries on the same theme, 5+ ERROR entries total, 10+ days of logs, 21+ days since last crystallization).

```
cogmem signals
```

No flags. Always outputs JSON.

**Example:**

```bash
cogmem signals
```

```json
{
  "should_crystallize": true,
  "reasons": [
    "10+ days of logs accumulated",
    "3+ PATTERN entries on same theme: skill-tracking"
  ],
  "last_crystallization": "2026-03-10",
  "days_since": 17
}
```

---

### `cogmem watch`

Detect patterns from git commit history. Counts fix/revert commits, detects log gaps (commits without corresponding log entries), and identifies workflow patterns.

```
cogmem watch [--since SINCE] [--json] [--auto-log]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--since` | `today` | Git log `--since` value (e.g., `"8 hours ago"`, `"2026-03-25"`) |
| `--json` | `false` | Output as JSON |
| `--auto-log` | `false` | Auto-append detected patterns to today's session log |

**Example:**

```bash
cogmem watch --since "8 hours ago"
```

```
Commits: 14 | Log entries: 6 | Fix: 3 | Revert: 1
  [PATTERN] Repeated fix commits (3x)
  [ERROR] Revert detected
```

**JSON output** (`--json`):

```json
{
  "fix_count": 3,
  "revert_count": 1,
  "entries": [
    {"category": "PATTERN", "title": "Repeated fix commits (3x)", "content": "...", "arousal": 0.7}
  ],
  "log_gap": {"has_gap": true, "severity": "medium"},
  "commit_count": 14,
  "log_entry_count": 6
}
```

---

### `cogmem decay`

Apply memory decay to consolidated logs. Compacts low-arousal entries older than the configured threshold while preserving vivid/active memories.

```
cogmem decay [--dry-run] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | `false` | Preview changes without modifying files |
| `--json` | `false` | Output as JSON |

Requires `decay.enabled = true` in `cogmem.toml`.

**Example:**

```bash
cogmem decay --dry-run
```

```
Memory decay (dry run):
  Kept (vivid/active): 42
  Compacted:           8
  Skipped:             3
```

---

## 4. Skills

All skills commands are under the `cogmem skills` subcommand group.

### `cogmem skills list`

List skills from the database, ranked by effectiveness.

```
cogmem skills list [--category CAT] [--top N] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--category` | *(all)* | Filter by category |
| `--top` | `10` | Show top N skills |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills list --top 5
```

```
ID                   Name                      Category           Effectiveness Executions
------------------------------------------------------------------------------------------
skill_abc123...      Git Workflow              automation-skills  0.850        12
skill_def456...      Error Recovery            meta-skills        0.780        8

Total: 2 skills
```

---

### `cogmem skills search`

Search skills by keyword query.

```
cogmem skills search QUERY [--top-k N] [--category CAT] [--json]
```

| Argument/Flag | Default | Description |
|---------------|---------|-------------|
| `QUERY` | *(required)* | Search query |
| `--top-k` | `5` | Number of results |
| `--category` | *(all)* | Filter by category |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills search "deployment"
```

```
Found 2 skills for query: 'deployment'

ID                   Name                      Category           Effectiveness
--------------------------------------------------------------------------------
skill_abc123...      Deploy Pipeline           automation-skills  0.900
skill_def456...      Rollback Recovery         automation-skills  0.750
```

---

### `cogmem skills show`

Show detailed information for a single skill.

```
cogmem skills show SKILL_ID [--json]
```

| Argument/Flag | Default | Description |
|---------------|---------|-------------|
| `SKILL_ID` | *(required)* | Skill ID to display |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills show skill_abc123
```

```
Skill Details: Git Workflow
==================================================
ID: skill_abc123
Category: automation-skills
Description: Automate git commit and push workflow

Performance:
  Average Effectiveness: 0.850
  Total Executions: 12
  Successful Executions: 10
  Success Rate: 83.3%
  Last Used: 2026-03-26

Created: 2026-03-15
Updated: 2026-03-26
Version: 3
```

---

### `cogmem skills stats`

Show aggregate skills statistics.

```
cogmem skills stats [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills stats
```

```
Skills Statistics
==============================
Total Skills: 15
Average Effectiveness: 0.720
Total Executions: 84
Overall Success Rate: 0.810

Skills by Category:
  automation-skills: 8
  meta-skills: 5
  communication-skills: 2

Top Performing Skills:
  1. Deploy Pipeline (0.920)
  2. Error Recovery (0.850)
  3. Git Workflow (0.830)
```

---

### `cogmem skills create`

Create a new skill from a context description. The system auto-categorizes and names the skill.

```
cogmem skills create CONTEXT [--effectiveness N] [--user-satisfaction N] [--feedback TEXT]
```

| Argument/Flag | Default | Description |
|---------------|---------|-------------|
| `CONTEXT` | *(required)* | Context description for skill creation |
| `--effectiveness` | `0.5` | Initial effectiveness score (0-1) |
| `--user-satisfaction` | `0.5` | Initial user satisfaction score (0-1) |
| `--feedback` | `""` | User feedback text |

**Example:**

```bash
cogmem skills create "Automated deployment with rollback on failure"
```

```
Created new skill: Automated Deployment With Rollback
ID: skill_1774569617_abc123
Category: automation-skills
```

---

### `cogmem skills delete`

Delete a skill by ID.

```
cogmem skills delete SKILL_ID
```

| Argument | Description |
|----------|-------------|
| `SKILL_ID` | Skill ID to delete |

**Example:**

```bash
cogmem skills delete skill_abc123
```

```
Deleted skill: skill_abc123
```

---

### `cogmem skills learn`

Execute the learning loop: analyze performance, select/create a skill, and record learning metrics.

```
cogmem skills learn CONTEXT --effectiveness N --user-satisfaction N \
  [--execution-time MS] [--error-rate N] [--feedback TEXT] [--json]
```

| Argument/Flag | Default | Description |
|---------------|---------|-------------|
| `CONTEXT` | *(required)* | Context description for learning |
| `--effectiveness` | *(required)* | Effectiveness score (0-1) |
| `--user-satisfaction` | *(required)* | User satisfaction score (0-1) |
| `--execution-time` | `1000` | Execution time in milliseconds |
| `--error-rate` | `0.0` | Error rate (0-1) |
| `--feedback` | `""` | User feedback text |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills learn "Deployed to production with zero downtime" \
  --effectiveness 0.9 --user-satisfaction 0.95
```

```
Learning Loop Results
==============================
Skills Analyzed: 3
Selected Skill: Deploy Pipeline
Learning Action: update
Performance Level: high
```

---

### `cogmem skills audit`

Audit skills and recommend improvements. Identifies skills that need improvement, suggests new skills, and flags stale ones.

```
cogmem skills audit [--brief] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--brief` | `false` | Quick check (skip slow scans) |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills audit --brief
```

```
Skill Audit Results
==================================================
Total skills: 15
Needs improvement: 2
Suggested new: 1
Stale: 3

Recommendations:
  1. [IMPROVE] !! Git Workflow
     Reason: effectiveness below 0.5 for last 5 executions
  2. [STALE] ! Legacy Deploy
     Reason: not used in 30+ days
  3. [CREATE] !!! CI/CD Pipeline
     Reason: repeated pattern detected in logs
```

---

### `cogmem skills review`

Full skill health review with status, trend, and recommendations for every skill.

```
cogmem skills review [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills review
```

```
Skill Health Review
============================================================
Total: 15  Healthy: 10  Critical: 2  New: 3

Status   Name                          Eff  Trend  Exec  Ver
------------------------------------------------------------
[OK]     Deploy Pipeline              0.92     ^     12    3
[OK]     Error Recovery               0.85     -      8    2
[!!]     Git Workflow                  0.45     v     15    4
[XX]     Legacy Deploy                0.20     v      3    1
[  ]     New Skill                    0.50     -      1    1

Recommendations (2):
------------------------------------------------------------
  1. [IMPROVE] !! Git Workflow
     effectiveness below threshold
  2. [STALE] ! Legacy Deploy
     not used in 30+ days

Run /skill-improve <name> to start improvement loop.
```

---

### `cogmem skills export`

Export skills from the database to `.claude/skills/` as markdown files with YAML frontmatter.

```
cogmem skills export [--output-dir DIR] [--force] [--quiet]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--output-dir` | `.claude/skills/` | Output directory |
| `--force` | `false` | Overwrite existing files |
| `--quiet` | `false` | Suppress per-file output |

**Example:**

```bash
cogmem skills export
```

```
Exported: .claude/skills/deploy-pipeline.md
Exported: .claude/skills/error-recovery.md

Exported 2 skills to .claude/skills
```

---

### `cogmem skills import`

Import skills from `.claude/skills/` markdown files into the database.

```
cogmem skills import SOURCE_DIR [--force] [--quiet]
```

| Argument/Flag | Default | Description |
|---------------|---------|-------------|
| `SOURCE_DIR` | *(required)* | Directory containing skill markdown files |
| `--force` | `false` | Overwrite existing skills in DB |
| `--quiet` | `false` | Suppress per-file output |

**Example:**

```bash
cogmem skills import .claude/skills/
```

```
Imported: memory-recall.md -> Memory Recall (skill_abc123)
Imported: deploy.md -> Deploy (skill_def456)

Imported 2 skills from .claude/skills
```

---

### `cogmem skills ingest`

Ingest benchmark results from the skill-creator plugin. Reads `benchmark.json` / `grading.json` from the workspace and updates skill metrics.

```
cogmem skills ingest --benchmark PATH --skill-name NAME [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--benchmark` | *(required)* | Path to benchmark workspace directory |
| `--skill-name` | *(required)* | Skill name to update |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills ingest --benchmark /tmp/skill-bench --skill-name "deploy-pipeline"
```

```
Benchmark Ingested
==============================
Skill: deploy-pipeline
Skill ID: skill_abc123
Source: /tmp/skill-bench
Effectiveness: 0.850
Error Rate: 0.050
Execution Time: 2400ms
```

---

### `cogmem skills track`

Track a skill deviation event during a session. Used for recording extra steps, skipped steps, error recoveries, and user corrections.

```
cogmem skills track SKILL_NAME --event TYPE --description TEXT [--step REF] [--date DATE]
```

| Argument/Flag | Default | Description |
|---------------|---------|-------------|
| `SKILL_NAME` | *(required)* | Skill name (directory name) |
| `--event` | *(required)* | Event type: `extra_step`, `skipped_step`, `error_recovery`, `user_correction` |
| `--description` | *(required)* | What happened |
| `--step` | *(none)* | Step reference (e.g., `"Step 3"`) |
| `--date` | today | Session date (YYYY-MM-DD) |

**Example:**

```bash
cogmem skills track "deploy-pipeline" \
  --event extra_step \
  --description "Added health check before cutover" \
  --step "Step 4"
```

```
Tracked: extra_step for deploy-pipeline
```

---

### `cogmem skills track-summary`

Summarize tracked events for a session. Shows which skills had issues and which ran smoothly.

```
cogmem skills track-summary [--date DATE] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--date` | today | Session date (YYYY-MM-DD) |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem skills track-summary --date 2026-03-26
```

```
Skills needing improvement:
  [deploy-pipeline] extra steps detected
    - extra_step (Step 4): Added health check before cutover

Skills OK (no issues): error-recovery, git-workflow
```

**JSON output** (`--json`):

```json
{
  "skills_used": [
    {
      "skill_name": "deploy-pipeline",
      "needs_improvement": true,
      "reason": "extra steps detected",
      "events": [
        {
          "event_type": "extra_step",
          "step_ref": "Step 4",
          "description": "Added health check before cutover"
        }
      ]
    }
  ],
  "skills_ok": ["error-recovery", "git-workflow"]
}
```

---

### `cogmem skills resolve`

Mark tracked events for a skill as resolved after updating the SKILL.md file. Increments the skill version.

```
cogmem skills resolve SKILL_NAME
```

| Argument | Description |
|----------|-------------|
| `SKILL_NAME` | Skill name to resolve |

**Example:**

```bash
cogmem skills resolve deploy-pipeline
```

```
Resolved 3 events for deploy-pipeline
```

---

## 5. Identity

All identity commands are under the `cogmem identity` subcommand group.

### `cogmem identity show`

Show the contents of identity files (`user.md` and/or `soul.md`), parsed by section.

```
cogmem identity show [--target TARGET]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target` | *(both)* | `user` or `soul`. Omit to show both. |

**Example:**

```bash
cogmem identity show --target user
```

```
=== User Profile (identity/user.md) ===

## Name
Akira

## Role
Engineering consultant

## Timezone
Asia/Tokyo (GMT+9)
```

---

### `cogmem identity update`

Update sections in an identity file. Supports single-section or batch (JSON) updates.

```
cogmem identity update --target TARGET [--section HEADING --content TEXT] [--json JSON_OBJ]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target` | *(required)* | `user` or `soul` |
| `--section` | *(none)* | Section heading to update (use with `--content`) |
| `--content` | *(none)* | New content for the section |
| `--json` | *(none)* | JSON object of `{"section": "content"}` pairs for batch update |

**Example (single section):**

```bash
cogmem identity update --target user --section "Timezone" --content "Asia/Tokyo (GMT+9)"
```

```
Updated [Timezone] in user.md
```

**Example (batch):**

```bash
cogmem identity update --target user --json '{"Name": "Akira", "Role": "Consultant"}'
```

```
Updated 2 sections in user.md
```

---

### `cogmem identity detect`

Detect placeholder (unfilled) sections in identity files.

```
cogmem identity detect [--target TARGET] [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target` | *(both)* | `user` or `soul`. Omit to check both. |
| `--json` | `false` | Output as JSON |

**Example:**

```bash
cogmem identity detect
```

```
user/Name: filled
user/Role: filled
user/Timezone: placeholder
soul/Personality: filled
soul/Values: placeholder
```

**JSON output** (`--json`):

```json
{
  "user": {
    "Name": false,
    "Role": false,
    "Timezone": true
  },
  "soul": {
    "Personality": false,
    "Values": true
  }
}
```

(`true` = placeholder, `false` = filled)

---

## 6. Dashboard

### `cogmem dashboard`

Start the web dashboard. Requires the `dashboard` extra (`pip install cogmem-agent[dashboard]`).

```
cogmem dashboard [--host HOST] [--port PORT] [--no-browser]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Host to bind |
| `--port` | `8765` | Port to bind |
| `--no-browser` | `false` | Don't auto-open browser |

**Example:**

```bash
cogmem dashboard --port 9000 --no-browser
```

```
Starting cogmem dashboard at http://127.0.0.1:9000
```
