# Configuration Reference

cogmem is configured via a `cogmem.toml` file placed at the root of your project. The CLI searches upward from the current directory to find it. You can also set the `COGMEM_CONFIG` environment variable to point to a specific file.

All paths are relative to the directory containing `cogmem.toml` unless specified as absolute.

---

## `[cogmem]` — General Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `logs_dir` | string | `"memory/logs"` | Directory where session log files (YYYY-MM-DD.md) are stored. |
| `contexts_dir` | string | `"memory/contexts"` | Directory for daily context files (YYYY-MM-DD.md). |
| `db_path` | string | `"memory/vectors.db"` | Path to the SQLite vector database. |
| `handover_delimiter` | string | `"## 引き継ぎ"` | Markdown heading used to detect the handover section in logs. |

---

## `[cogmem.embedding]` — Embedding Provider

Controls how text is converted to vector embeddings for semantic search.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | string | `"ollama"` | Embedding provider. Currently `"ollama"` is the primary supported provider. |
| `model` | string | `"zylonai/multilingual-e5-large"` | Model name to use for embedding generation. |
| `url` | string | `"http://localhost:11434/api/embed"` | API endpoint URL for the embedding service. |
| `timeout` | integer | `10` | Request timeout in seconds. Increase if running on slower hardware. |

See [embedding-providers.md](embedding-providers.md) for details on supported providers.

---

## `[cogmem.scoring]` — Search Scoring

Controls how search results are ranked. The final score is a weighted combination of cosine similarity and arousal, with time-based decay applied.

| Key | Type | Default | Valid Range | Description |
|-----|------|---------|-------------|-------------|
| `sim_weight` | float | `0.7` | 0.0 - 1.0 | Weight given to cosine similarity in the combined score. |
| `arousal_weight` | float | `0.3` | 0.0 - 1.0 | Weight given to arousal (emotional intensity) in the combined score. `sim_weight + arousal_weight` should equal 1.0. |
| `base_half_life` | float | `60.0` | > 0 | Half-life in days for time-based decay. After this many days, a memory's recency factor drops to 50%. Higher values make memories fade more slowly. |
| `decay_floor` | float | `0.3` | 0.0 - 1.0 | Minimum recency factor. Even very old memories will not decay below this value. Prevents complete forgetting. |

**Score formula**: `score = (sim_weight * similarity + arousal_weight * arousal) * recency_factor`

Where `recency_factor = max(decay_floor, 0.5 ^ (age_days / base_half_life))`

---

## `[cogmem.identity]` — Identity File Paths

Paths to the agent and user identity definition files.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `soul` | string | `"identity/soul.md"` | Path to the agent identity file (personality, values, communication style). |
| `user` | string | `"identity/user.md"` | Path to the user profile file (name, role, preferences). |

> **Migration note**: The legacy key `agent` is still accepted but deprecated. Rename it to `soul` and run `cogmem migrate`.

---

## `[cogmem.knowledge]` — Knowledge File Paths

Paths to accumulated knowledge files updated during memory crystallization.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `summary` | string | `"memory/knowledge/summary.md"` | Path to the knowledge summary file (established principles, active projects). |
| `error_patterns` | string | `"memory/knowledge/error-patterns.md"` | Path to the error patterns file (EP-NNN entries extracted from past mistakes). |

---

## `[cogmem.session]` — Session Initialization

Controls how session initialization loads context from recent logs.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `recent_logs` | integer | `2` | Number of recent log files to read during Session Init. |
| `prefer_compact` | boolean | `true` | When `true`, prefer `.compact.md` files over full logs if they exist. Reduces token usage. |
| `token_budget` | integer | `6000` | Target token budget for Session Init context. If exceeded, the agent recommends running `/compact`. |

---

## `[cogmem.crystallization]` — Memory Consolidation

Thresholds that trigger the crystallization process (extracting reusable knowledge from logs).

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `pattern_threshold` | integer | `3` | Number of `[PATTERN]` entries on the same theme required to trigger schema extraction. |
| `error_threshold` | integer | `5` | Cumulative `[ERROR]` entries required to trigger error pattern consolidation. |
| `log_days_threshold` | integer | `10` | Minimum number of log files (days) before crystallization can trigger. |
| `checkpoint_interval_days` | integer | `21` | Minimum days since the last checkpoint before crystallization runs again. |
| `last_checkpoint` | string | `""` | ISO date (YYYY-MM-DD) of the last crystallization run. Managed automatically. |
| `checkpoint_count` | integer | `0` | Total number of crystallization runs completed. Managed automatically. |

Crystallization runs automatically during Wrap when any signal condition is met.

---

## `[cogmem.decay]` — Memory Forgetting

Controls which memories are candidates for permanent deletion.

| Key | Type | Default | Valid Range | Description |
|-----|------|---------|-------------|-------------|
| `enabled` | boolean | `true` | — | Master switch for the forgetting system. Set to `false` to retain all memories indefinitely. |
| `arousal_threshold` | float | `0.7` | 0.0 - 1.0 | Memories with arousal at or above this value are permanently retained regardless of recall frequency. |
| `recall_threshold` | integer | `2` | >= 0 | Memories recalled this many times or more are candidates for retention. |
| `recall_window_months` | integer | `18` | > 0 | If a memory has not been recalled within this window, it becomes a deletion candidate (unless protected by arousal). |

---

## `[cogmem.context_search]` — Context Search

Settings for context-aware search and flashback detection. This section is not present in the default template but is supported in the configuration.

| Key | Type | Default | Valid Range | Description |
|-----|------|---------|-------------|-------------|
| `enabled` | boolean | `true` | — | Enable or disable context search features. |
| `flashback_sim` | float | `0.65` | 0.0 - 1.0 | Minimum similarity score for a memory to be surfaced as a flashback. |
| `flashback_arousal` | float | `0.5` | 0.0 - 1.0 | Minimum arousal for a memory to qualify as a flashback. |
| `cache_max_size` | integer | `20` | > 0 | Maximum number of entries in the context search cache. |
| `cache_sim_threshold` | float | `0.9` | 0.0 - 1.0 | Similarity threshold for cache hits. Queries above this similarity to a cached query reuse the cached result. |

---

## `[cogmem.skills]` — Skill Management

Controls automatic skill improvement behavior during Wrap.

| Key | Type | Default | Options | Description |
|-----|------|---------|---------|-------------|
| `auto_improve` | string | `"auto"` | `"auto"`, `"ask"`, `"off"` | How to handle skill improvements detected during Wrap. `"auto"` applies improvements automatically. `"ask"` prompts the user for confirmation. `"off"` disables skill improvement entirely. |

---

## `[cogmem.metrics]` — Usage Metrics

Counters managed automatically by the system.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `total_sessions` | integer | `0` | Total number of completed sessions. Incremented automatically during Wrap. |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `COGMEM_CONFIG` | Absolute path to a `cogmem.toml` file. When set, cogmem uses this file directly instead of searching upward from the current directory. |

---

## Complete Example

```toml
[cogmem]
logs_dir = "memory/logs"
contexts_dir = "memory/contexts"
db_path = "memory/vectors.db"
handover_delimiter = "## 引き継ぎ"

[cogmem.identity]
soul = "identity/soul.md"
user = "identity/user.md"

[cogmem.knowledge]
summary = "memory/knowledge/summary.md"
error_patterns = "memory/knowledge/error-patterns.md"

[cogmem.session]
recent_logs = 2
prefer_compact = true
token_budget = 6000

[cogmem.embedding]
provider = "ollama"
model = "zylonai/multilingual-e5-large"
url = "http://localhost:11434/api/embed"
timeout = 10

[cogmem.scoring]
sim_weight = 0.7
arousal_weight = 0.3
base_half_life = 60.0
decay_floor = 0.3

[cogmem.crystallization]
pattern_threshold = 3
error_threshold = 5
log_days_threshold = 10
checkpoint_interval_days = 21
last_checkpoint = ""
checkpoint_count = 0

[cogmem.decay]
enabled = true
arousal_threshold = 0.7
recall_threshold = 2
recall_window_months = 18

[cogmem.context_search]
enabled = true
flashback_sim = 0.65
flashback_arousal = 0.5
cache_max_size = 20
cache_sim_threshold = 0.9

[cogmem.skills]
auto_improve = "auto"

[cogmem.metrics]
total_sessions = 0
```
