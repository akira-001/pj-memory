# Dashboard User Guide

The cogmem dashboard is a web-based interface for visualizing and exploring all cognitive memory data -- episodic logs, skills, consolidation status, personality profiles, and semantic search.

## Getting Started

### Requirements

```bash
pip install cogmem-agent[dashboard]
```

### Launch

```bash
cogmem dashboard
```

Opens at **http://127.0.0.1:8765** by default.

### Language Switching

The sidebar footer has **EN / JA** buttons. Clicking one sets a cookie that persists across sessions (1-year expiry). All page titles, labels, and descriptions switch between English and Japanese.

---

## Pages

### 1. Memory Overview (`/`)

The landing page. Shows aggregate statistics across all indexed memories.

**Stat cards (top row):**

| Card | Description |
|------|-------------|
| Total Memories | Count of all memory entries, with start date and total days |
| Date Range | Earliest to latest memory date |
| Avg Arousal | Mean emotional intensity score (0.0--1.0 scale) |
| Categories | Number of distinct category tags, with per-category counts as badges |

**Charts:**

- **Daily Accumulation** -- Bar chart showing number of memory entries recorded per day. Useful for spotting active vs. quiet periods.
- **Category Breakdown** -- Doughnut chart showing distribution across INSIGHT, DECISION, ERROR, PATTERN, QUESTION, MILESTONE, and SKILL tags.
- **Arousal Distribution** -- Bar histogram with 6 buckets from 0.4 to 1.0, showing how many entries fall into each emotional intensity range.

**Most Recalled Memories:**

A table listing the top 5 most-recalled memories, showing recall count, title (first 80 chars), arousal score, and last recall date.

**Consolidation Signals (bottom panel):**

Four signal indicators with current/threshold values:
- Pattern entries (e.g., 5 / 3)
- Error entries (e.g., 3 / 5)
- Log days (e.g., 12 / 10)
- Days since checkpoint (e.g., 25 / 21)

A green dot means the threshold is met. When enough conditions are met, a recommendation banner appears suggesting consolidation.

---

### 2. Episodic Memory (`/logs/`)

Browse session logs as a list of dates, then drill into individual days.

#### List View (`/logs/`)

**Summary cards (top row):**

| Card | Description |
|------|-------------|
| Total Logs | Number of distinct log dates |
| Detailed | Days with full `.md` logs |
| Compacted | Days where logs have been compressed to `.compact.md` |
| Retained | Days with both full and compact versions |

**Category Distribution chart:** Horizontal bar chart showing aggregate category counts across all log files.

**All Logs table:**

| Column | Description |
|--------|-------------|
| Date | Clickable link to the detail view |
| Status | Badge: Detailed (green), Compacted (grey), or Retained (blue) |
| Entries | Number of `###` entries in the log |
| Categories | Top 3 category tags with counts |
| Max Arousal | Highest arousal value in that day's entries |
| Overview | First 60 characters of the session overview |

#### Detail View (`/logs/{date}`)

Shows a single day's log with interactive filtering.

**Session Overview:** Card at the top displaying the session summary text.

**Filter bar:**
- **Category dropdown** -- Filter by INSIGHT, DECISION, ERROR, PATTERN, QUESTION, or MILESTONE
- **Sort dropdown** -- Sort by Time (chronological) or Arousal (highest first)
- **Search box** -- Free-text search across entry titles and bodies (live filtering with 500ms debounce via HTMX)

**Entries list:** Each entry shows its category badge, arousal score, emotion tag, title, and body text.

**Handover section:** Card at the bottom showing the session handover notes (continuing themes, next actions, cautions).

All filters update the entries list dynamically without page reload (HTMX partial at `/logs/api/entries`).

---

### 3. Memory Consolidation (`/consolidation/`)

Monitors the knowledge consolidation pipeline -- when enough experience accumulates, it gets distilled into principles and error patterns.

**Consolidation Signals table:**

| Column | Description |
|--------|-------------|
| Condition | What is being measured (pattern entries, error entries, log days, days since checkpoint) |
| Current | Current accumulated value |
| Threshold | Value needed to trigger consolidation |
| Status | "Ready" (green) or "Accumulating" (grey) |

A warning banner appears when consolidation is recommended.

**Checkpoint section:** Two stat cards showing the last checkpoint date and total checkpoint count.

**Error Patterns table:** Lists extracted error patterns (EP-001, EP-002, etc.) with ID, title, and occurrence date. These are recurring mistakes with root causes and countermeasures, parsed from `error-patterns.md`.

**Memory Decay Settings form:** Configurable parameters that control how memories fade over time.

| Setting | Description | Default |
|---------|-------------|---------|
| Arousal Threshold | Entries with arousal >= this value are kept permanently | 0.7 |
| Recall Threshold | Entries recalled >= this many times are retention candidates | 2 |
| Recall Window (months) | If not recalled within this period, memory fades | 18 |
| Decay Enabled | Master toggle for the decay system | checkbox |

Submitting the form saves to `cogmem.toml` and updates the running config.

**Established Principles:** Decision-making rules extracted from repeated patterns across sessions. Each principle has a title and body rendered from the knowledge summary markdown.

---

### 4. Skills (`/skills/`)

Tracks skill effectiveness, usage patterns, and improvement recommendations.

#### List View (`/skills/`)

**Audit Summary cards:**

| Card | Description |
|------|-------------|
| Total | Number of registered skills |
| Needs Improvement | Skills flagged for revision |
| Suggested New | New skills recommended by the auditor |
| Stale | Skills that haven't been used recently |

**Recommendations panel:** If the skill auditor has suggestions, they appear as a list with priority dots (green = high) and type badges (improve / create / retire).

**Skills table:**

| Column | Description |
|--------|-------------|
| Name | Skill name with description subtitle |
| Category | Skill category badge |
| Effectiveness | Progress bar (green >= 0.7, yellow >= 0.5, red < 0.5) with numeric score |
| Executions | Total execution count from learning data |
| Events | Count of tracked session events (start, end, deviations) |
| Version | Current version with improvement count |
| Last Used | Date of most recent use |
| Trend | Arrow up/down, "new" badge, or flat dash |

**Clicking a row** opens a detail modal (loaded via HTMX from `/skills/api/detail/{id}`).

#### Detail Modal

Shows comprehensive information for one skill:

- **Header:** Name, category badge, description
- **Stats:** Effectiveness score with bar, execution count (with success count), version with last update date
- **Execution Pattern:** If defined, shows the skill's typical execution pattern
- **Effectiveness Trend:** Line chart showing effectiveness over time (up to 50 data points)
- **Events Timeline:** Last 10 session events with type badges (skill_start, skill_end, error_recovery, user_correction, extra_step, skipped_step) and descriptions
- **Recent Usage:** Table of last 10 usage log entries with date, effectiveness score (color-coded), and context

A link at the bottom opens the full skill detail page (`/skills/{id}`).

---

### 5. Personality (`/personality/`)

Displays the user profile and agent identity side by side, plus learning history.

**User & Agent panels (two-column grid):**

- **User panel:** Sections parsed from `identity/user.md` (basic info, expertise, communication preferences, decision patterns, interests). Each section heading and content is displayed.
- **Agent panel:** Sections parsed from `identity/soul.md` (name, role, core values, thinking style, communication style, limitations). Same section layout.

Both panels show "No data available yet" when their respective identity files are empty or missing.

**Learning Timeline:** A chronological list of INSIGHT entries from the memories database (up to 50, newest first). Each item shows the date, insight title, and first 200 characters of the body text. Represents key learnings extracted from sessions.

**Knowledge Summary:** Renders the full content of `memory/knowledge/summary.md` -- established principles, error patterns reference, and active project status.

---

### 6. Memory Search (`/search/`)

Semantic search across all indexed memories using vector similarity.

**Memory Index card:** Shows total indexed memories and number of days covered, with a sparkline chart showing daily memory accumulation over time.

**Search box:** Text input with a Search button. Submitting a query triggers an HTMX request to `/search/api/results` that returns results without a full page reload. A "Searching..." indicator appears during the request.

**Top Keywords:** When no query is active, displays the 10 most frequent keywords extracted from memory titles as clickable pill-shaped tags. Each shows the word and its frequency count. Clicking a keyword fills the search with that term. Stop words (common Japanese particles and English function words) are filtered out.

**Search results:** Each result card shows:

| Element | Description |
|---------|-------------|
| Score | Similarity score (0.00--1.00) |
| Date | Date of the memory entry |
| Source | Badge indicating origin (e.g., log type) |
| Arousal | Emotional intensity of the original entry |
| Content | First 300 characters of the memory content |
| View log | Link to the corresponding log detail page |

**Status line:** Shows the search backend status and result count.

---

## Navigation

The sidebar is always visible on the left side with links to all six pages:
- Memory Overview
- Episodic Memory
- Memory Consolidation
- Skills
- Personality
- Memory Search

The active page is highlighted. The language switch (EN/JA) is at the bottom of the sidebar.

## Technical Notes

- **HTMX** is used for dynamic partial updates (search results, log entry filtering, skill detail modals) without full page reloads.
- **Chart.js 4** renders all charts (bar, doughnut, line, sparkline).
- Data is read directly from the cogmem SQLite database, markdown log files, and identity files at request time. There is no caching layer.
- The dashboard is read-only except for the Memory Decay Settings form on the Consolidation page, which writes to `cogmem.toml`.
