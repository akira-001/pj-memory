# API Reference

Python API reference for the `cognitive-memory` library.

---

## Table of Contents

- [Types](#types) — `cognitive_memory.types`
- [Config](#config) — `cognitive_memory.config`
- [MemoryStore](#memorystore) — `cognitive_memory.store`
- [Parser](#parser) — `cognitive_memory.parser`
- [Scoring](#scoring) — `cognitive_memory.scoring`
- [Decay](#decay) — `cognitive_memory.decay`
- [Signals](#signals) — `cognitive_memory.signals`
- [Context](#context) — `cognitive_memory.context`
- [Identity](#identity) — `cognitive_memory.identity`

---

## Types

**Module:** `cognitive_memory.types`

Core data classes used throughout the library.

### `MemoryEntry`

A single parsed log entry.

```python
@dataclass
class MemoryEntry:
    date: str
    content: str
    arousal: float = 0.5
    category: Optional[str] = None
```

| Field | Type | Description |
|-------|------|-------------|
| `date` | `str` | Date string in `YYYY-MM-DD` format |
| `content` | `str` | Full text content of the log entry |
| `arousal` | `float` | Emotional intensity score (0.0–1.0). Default `0.5` |
| `category` | `Optional[str]` | Entry category tag: `INSIGHT`, `DECISION`, `ERROR`, `PATTERN`, `QUESTION`, `MILESTONE`, `SUMMARY`, or `None` |

### `SearchResult`

A single search result with scoring metadata.

```python
@dataclass
class SearchResult:
    score: float
    date: str
    content: str
    arousal: float
    source: str
    cosine_sim: Optional[float] = None
    time_decay: Optional[float] = None
    content_hash: Optional[str] = None
```

| Field | Type | Description |
|-------|------|-------------|
| `score` | `float` | Combined relevance score |
| `date` | `str` | Date of the memory entry |
| `content` | `str` | Full text content |
| `arousal` | `float` | Arousal value of the entry |
| `source` | `str` | `"semantic"` or `"grep"` |
| `cosine_sim` | `Optional[float]` | Cosine similarity to query (semantic results only) |
| `time_decay` | `Optional[float]` | Time decay factor applied |
| `content_hash` | `Optional[str]` | SHA-256 hash for recall reinforcement |

### `SearchResponse`

Aggregated search response.

```python
@dataclass
class SearchResponse:
    results: List[SearchResult] = field(default_factory=list)
    status: str = "ok"
```

| Field | Type | Description |
|-------|------|-------------|
| `results` | `List[SearchResult]` | List of search results |
| `status` | `str` | `"ok"`, `"skipped_by_gate"`, `"disabled"`, `"degraded (reason)"`, or with `"(cached)"` suffix |

---

## Config

**Module:** `cognitive_memory.config`

### `CogMemConfig`

Configuration dataclass with all tunable parameters. Loads from `cogmem.toml` or uses defaults.

```python
@dataclass
class CogMemConfig:
    ...
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `logs_dir` | `str` | `"memory/logs"` | Path to log files directory |
| `db_path` | `str` | `"memory/vectors.db"` | Path to SQLite vector database |
| `handover_delimiter` | `str` | `"## 引き継ぎ"` | Delimiter marking handover section (excluded from parsing) |
| `sim_weight` | `float` | `0.7` | Weight for cosine similarity in combined scoring |
| `arousal_weight` | `float` | `0.3` | Weight for arousal in combined scoring |
| `base_half_life` | `float` | `60.0` | Base half-life in days for time decay |
| `decay_floor` | `float` | `0.3` | Minimum time decay value |
| `embedding_provider` | `str` | `"ollama"` | Embedding provider name |
| `embedding_model` | `str` | `"zylonai/multilingual-e5-large"` | Embedding model identifier |
| `embedding_url` | `str` | `"http://localhost:11434/api/embed"` | Embedding API endpoint URL |
| `embedding_timeout` | `int` | `10` | Embedding request timeout in seconds |
| `context_search_enabled` | `bool` | `True` | Enable/disable context search |
| `context_flashback_sim` | `float` | `0.65` | Minimum cosine similarity for flashback filtering |
| `context_flashback_arousal` | `float` | `0.5` | Minimum arousal for flashback filtering |
| `context_cache_max_size` | `int` | `20` | Maximum entries in the search cache |
| `context_cache_sim_threshold` | `float` | `0.9` | Similarity threshold for cache hits |
| `decay_arousal_threshold` | `float` | `0.7` | Arousal threshold for decay evaluation (keep vivid memories) |
| `decay_recall_threshold` | `int` | `2` | Minimum recall count for recall-based retention |
| `decay_recall_window_months` | `int` | `18` | Months for recall window in decay evaluation |
| `decay_enabled` | `bool` | `True` | Enable/disable memory decay |
| `pattern_threshold` | `int` | `3` | PATTERN entries needed to trigger crystallization |
| `error_threshold` | `int` | `5` | ERROR entries needed to trigger crystallization |
| `log_days_threshold` | `int` | `10` | Log days needed to trigger crystallization |
| `checkpoint_interval_days` | `int` | `21` | Days since last checkpoint to trigger crystallization |
| `skills_auto_improve` | `str` | `"auto"` | Skill auto-improvement mode: `"auto"`, `"ask"`, or `"off"` |

#### Resolved Path Properties

| Property | Returns | Description |
|----------|---------|-------------|
| `logs_path` | `Path` | Absolute path to log files directory |
| `database_path` | `Path` | Absolute path to SQLite database |
| `contexts_path` | `Path` | Absolute path to contexts directory |
| `identity_soul_path` | `Path` | Absolute path to soul identity file |
| `identity_user_path` | `Path` | Absolute path to user identity file |
| `knowledge_summary_path` | `Path` | Absolute path to knowledge summary file |
| `knowledge_error_patterns_path` | `Path` | Absolute path to error patterns file |

#### Class Methods

##### `CogMemConfig.from_toml(path: str | Path) -> CogMemConfig`

Load configuration from a TOML file.

```python
config = CogMemConfig.from_toml("cogmem.toml")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str \| Path` | Path to the TOML configuration file |

**Returns:** `CogMemConfig` instance with values from the file.

**Raises:** `ImportError` if `tomli` is not installed on Python < 3.11.

##### `CogMemConfig.find_and_load(start_dir: Optional[str | Path] = None) -> CogMemConfig`

Search for `cogmem.toml` from `start_dir` upward through parent directories. Falls back to the `COGMEM_CONFIG` environment variable, then defaults.

```python
config = CogMemConfig.find_and_load()
config = CogMemConfig.find_and_load("/path/to/project")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_dir` | `Optional[str \| Path]` | Directory to start searching from. Defaults to `cwd()` |

**Returns:** `CogMemConfig` instance.

---

## MemoryStore

**Module:** `cognitive_memory.store`

Main interface for indexing and searching cognitive memories.

```python
class MemoryStore:
    def __init__(
        self,
        config: Optional[CogMemConfig] = None,
        embedder: Optional[object] = None,
    ): ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `Optional[CogMemConfig]` | Configuration instance. Uses defaults if `None` |
| `embedder` | `Optional[object]` | Custom embedding provider. Auto-creates `OllamaEmbedding` if `None` |

Supports context manager protocol:

```python
with MemoryStore(config) as store:
    store.index_dir()
    response = store.search("deployment issue")
```

### `index_file(filepath: Path, force: bool = False) -> int`

Index a single log file into the vector database.

| Parameter | Type | Description |
|-----------|------|-------------|
| `filepath` | `Path` | Path to a markdown log file (filename must start with `YYYY-MM-DD`) |
| `force` | `bool` | Re-index even if file hasn't changed since last indexing |

**Returns:** Number of entries stored (int).

```python
count = store.index_file(Path("memory/logs/2026-03-25.md"))
```

### `index_dir(force: bool = False) -> int`

Index all log files in the configured logs directory. Automatically prefers original `.md` files over `.compact.md` files, falling back to compact when the original yielded zero entries.

| Parameter | Type | Description |
|-----------|------|-------------|
| `force` | `bool` | Force re-index all files |

**Returns:** Total number of entries stored across all files (int).

```python
total = store.index_dir()
total = store.index_dir(force=True)
```

### `search(query: str, top_k: int = 5) -> SearchResponse`

Full search pipeline with query gate check and recall reinforcement. Combines semantic search (vector similarity) with grep-based keyword search, merges and deduplicates results.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Search query string |
| `top_k` | `int` | Maximum number of results to return |

**Returns:** `SearchResponse` with results and status.

If the query is rejected by the gate (too short/trivial), returns `status="skipped_by_gate"`. Falls back to grep-only search if the embedding service is unavailable (`status="degraded (...)"`)

```python
response = store.search("error pattern in deployment")
for result in response.results:
    print(f"[{result.date}] score={result.score:.2f} {result.content[:80]}")
```

### `context_search(query: str, cache: Optional[SearchCache] = None, session_keywords: Optional[List[str]] = None, top_k: int = 3) -> SearchResponse`

Context-aware search with session caching and flashback filtering. Designed for automatic background search during conversations.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Search query string |
| `cache` | `Optional[SearchCache]` | Session-scoped cache for deduplication across calls |
| `session_keywords` | `Optional[List[str]]` | Keywords that force the gate to pass for short queries |
| `top_k` | `int` | Maximum results before flashback filtering |

**Returns:** `SearchResponse` — results filtered to high-relevance flashback candidates.

```python
from cognitive_memory.context import SearchCache

cache = SearchCache(max_size=20, sim_threshold=0.9)
response = store.context_search(
    "cogmem architecture",
    cache=cache,
    session_keywords=["cogmem", "architecture"],
)
```

### `reinforce_recall(content_hash: str, arousal_boost: float = 0.1) -> None`

Record a recall event for a memory entry. Increments the recall count, boosts arousal (capped at 1.0), and updates the last-recalled timestamp.

| Parameter | Type | Description |
|-----------|------|-------------|
| `content_hash` | `str` | SHA-256 hash of the memory content |
| `arousal_boost` | `float` | Amount to increase arousal by (capped at 1.0) |

```python
store.reinforce_recall("abc123...", arousal_boost=0.15)
```

### `status() -> dict`

Return index statistics.

**Returns:** Dict with keys: `indexed_files` (int), `total_entries` (int), `db_size_bytes` (int).

```python
stats = store.status()
# {"indexed_files": 42, "total_entries": 318, "db_size_bytes": 2097152}
```

### `close() -> None`

Close the database connection. Called automatically when used as a context manager.

### `_execute_search(query: str, top_k: int = 5) -> SearchResponse`

Core search pipeline without gate check. Useful when the caller handles gating externally (e.g., `context_search`).

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Search query string |
| `top_k` | `int` | Maximum number of results |

**Returns:** `SearchResponse` with merged semantic + grep results.

---

## Parser

**Module:** `cognitive_memory.parser`

### `parse_entries(md_text: str, date: str, handover_delimiter: str = "## 引き継ぎ") -> Iterator[MemoryEntry]`

Extract log entries from a markdown session log. Parses three formats:
1. Session overview (`## セッション概要`) as a `SUMMARY` entry
2. Standard heading entries (`### [CATEGORY] Title`)
3. Compact list entries (`- [CATEGORY] text`)

Content after `handover_delimiter` is excluded.

| Parameter | Type | Description |
|-----------|------|-------------|
| `md_text` | `str` | Raw markdown text of a log file |
| `date` | `str` | Date string (`YYYY-MM-DD`) to assign to entries |
| `handover_delimiter` | `str` | Section delimiter to stop parsing at |

**Returns:** Iterator of `MemoryEntry` objects.

```python
from cognitive_memory.parser import parse_entries

text = Path("memory/logs/2026-03-25.md").read_text()
for entry in parse_entries(text, "2026-03-25"):
    print(f"[{entry.category}] arousal={entry.arousal} {entry.content[:60]}")
```

### `is_noise(content: str) -> bool`

Check if content is noise (too short or matches noise patterns like greetings).

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | `str` | Text to check |

**Returns:** `True` if the content is noise and should be filtered out.

---

## Scoring

**Module:** `cognitive_memory.scoring`

### `time_decay(entry_date: str, arousal: float, base_half_life: float = 60.0, floor: float = 0.3) -> float`

Forgetting curve with arousal-adaptive half-life and floor. High-arousal memories decay slower.

| Parameter | Type | Description |
|-----------|------|-------------|
| `entry_date` | `str` | ISO format date string of the memory |
| `arousal` | `float` | Arousal value (0.0–1.0) |
| `base_half_life` | `float` | Base half-life in days |
| `floor` | `float` | Minimum decay value (never fully forgotten) |

**Returns:** Decay factor between `floor` and `1.0`. Today's entries return `1.0`.

```python
from cognitive_memory.scoring import time_decay

factor = time_decay("2026-01-15", arousal=0.9)  # high arousal → slow decay
factor = time_decay("2026-01-15", arousal=0.4)  # low arousal → fast decay
```

### `adaptive_half_life(arousal: float, base_half_life: float = 60.0) -> float`

Calculate arousal-adjusted half-life. Arousal of 1.0 doubles the base half-life.

| Parameter | Type | Description |
|-----------|------|-------------|
| `arousal` | `float` | Arousal value (0.0–1.0) |
| `base_half_life` | `float` | Base half-life in days |

**Returns:** Adjusted half-life in days (`base * (1 + arousal)`).

### `cosine_sim(a: List[float], b: List[float]) -> float`

Cosine similarity for pre-normalized vectors (dot product).

| Parameter | Type | Description |
|-----------|------|-------------|
| `a` | `List[float]` | Normalized vector |
| `b` | `List[float]` | Normalized vector |

**Returns:** Similarity score (-1.0 to 1.0).

### `normalize(vec: List[float]) -> List[float]`

L2-normalize a vector.

| Parameter | Type | Description |
|-----------|------|-------------|
| `vec` | `List[float]` | Input vector |

**Returns:** Unit-length vector. Returns input unchanged if norm is zero.

---

## Decay

**Module:** `cognitive_memory.decay`

Human-like memory forgetting mechanism.

### `DecayAction`

Enum defining possible decay actions for a memory entry.

```python
class DecayAction(Enum):
    KEEP = "keep"        # Vivid or actively recalled — preserve full detail
    COMPACT = "compact"  # Mundane — compress to one-line summary
    DELETE = "delete"     # Faded — remove detail (compact already exists)
```

### `evaluate_entry(arousal: float, recall_count: int, last_recalled: str | None, arousal_threshold: float = 0.7, recall_threshold: int = 2, recall_window_months: int = 18) -> DecayAction`

Evaluate whether a memory entry should be kept, compacted, or deleted. Models human memory retention:

1. **High arousal** (>= threshold) → always `KEEP`
2. **Frequently recalled AND recently recalled** → `KEEP`
3. **Frequently recalled BUT stale** → `DELETE`
4. **Everything else** → `COMPACT`

| Parameter | Type | Description |
|-----------|------|-------------|
| `arousal` | `float` | Arousal value of the entry |
| `recall_count` | `int` | Number of times the entry has been recalled |
| `last_recalled` | `str \| None` | ISO datetime of last recall, or `None` |
| `arousal_threshold` | `float` | Threshold for vivid memory retention |
| `recall_threshold` | `int` | Minimum recall count for recall-based retention |
| `recall_window_months` | `int` | Months within which recall is considered "recent" |

**Returns:** `DecayAction` enum value.

```python
from cognitive_memory.decay import evaluate_entry, DecayAction

action = evaluate_entry(arousal=0.9, recall_count=0, last_recalled=None)
assert action == DecayAction.KEEP  # high arousal → vivid memory

action = evaluate_entry(arousal=0.4, recall_count=5, last_recalled="2026-03-20T10:00:00")
assert action == DecayAction.KEEP  # frequently + recently recalled

action = evaluate_entry(arousal=0.4, recall_count=0, last_recalled=None)
assert action == DecayAction.COMPACT  # mundane, never recalled
```

### `apply_decay(config: CogMemConfig, dry_run: bool = False) -> dict`

Apply memory decay to all log files before the last checkpoint. For files where no entry qualifies as `KEEP`, generates a `.compact.md` summary and deletes the original.

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `CogMemConfig` | Configuration with paths and decay thresholds |
| `dry_run` | `bool` | If `True`, evaluate without modifying files |

**Returns:** Dict with counts: `{"kept": int, "compacted": int, "deleted": int, "skipped": int}`.

```python
from cognitive_memory.decay import apply_decay

result = apply_decay(config, dry_run=True)
print(f"Would compact {result['compacted']} files, keep {result['kept']}")
```

---

## Signals

**Module:** `cognitive_memory.signals`

Crystallization signal detection — determines when accumulated experience should be consolidated into permanent knowledge.

### `CrystallizationSignals`

Dataclass holding signal check results.

```python
@dataclass
class CrystallizationSignals:
    pattern_count: int = 0
    error_count: int = 0
    log_days: int = 0
    days_since_checkpoint: int = 0
    should_crystallize: bool = False
    triggered_conditions: List[str] = field(default_factory=list)
    pattern_threshold: int = 3
    error_threshold: int = 5
    log_days_threshold: int = 10
    checkpoint_interval_days: int = 21
```

| Field | Type | Description |
|-------|------|-------------|
| `should_crystallize` | `bool` | `True` if any condition is met |
| `triggered_conditions` | `List[str]` | Human-readable descriptions of triggered conditions |
| `pattern_count` | `int` | Number of `[PATTERN]` entries found |
| `error_count` | `int` | Number of `[ERROR]` entries found |
| `log_days` | `int` | Number of distinct log days |
| `days_since_checkpoint` | `int` | Days since last crystallization checkpoint |

#### `to_dict() -> dict`

Serialize to a plain dict for JSON output.

### `check_signals(config: CogMemConfig) -> CrystallizationSignals`

Scan all log files and check crystallization signal conditions.

Triggers when any of:
- `[PATTERN]` entries >= `pattern_threshold` (default 3)
- `[ERROR]` entries >= `error_threshold` (default 5)
- Log days >= `log_days_threshold` (default 10)
- Days since checkpoint >= `checkpoint_interval_days` (default 21)

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `CogMemConfig` | Configuration with paths and thresholds |

**Returns:** `CrystallizationSignals` instance.

```python
from cognitive_memory.signals import check_signals

signals = check_signals(config)
if signals.should_crystallize:
    for cond in signals.triggered_conditions:
        print(f"  - {cond}")
```

---

## Context

**Module:** `cognitive_memory.context`

Context search utilities: session cache and flashback filtering.

### `SearchCache`

Session-scoped in-memory cache for query embeddings and their search responses. Uses cosine similarity to detect duplicate queries.

```python
class SearchCache:
    def __init__(self, max_size: int = 20, sim_threshold: float = 0.9) -> None: ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `max_size` | `int` | Maximum cached entries (FIFO eviction) |
| `sim_threshold` | `float` | Cosine similarity threshold for cache hits |

#### `get(query_vec: List[float]) -> Optional[SearchResponse]`

Find a cached response whose stored query vector has similarity >= `sim_threshold` to the given vector.

**Returns:** `SearchResponse` if cache hit, `None` if miss.

#### `put(query_vec: List[float], response: SearchResponse) -> None`

Store a query-response pair. Evicts the oldest entry if cache is full.

#### `clear() -> None`

Remove all cached entries.

### `filter_flashbacks(results: List[SearchResult], sim_threshold: float = 0.65, arousal_threshold: float = 0.5) -> List[SearchResult]`

Filter search results for flashback candidates (involuntary memory recall).

- **Semantic results** (cosine_sim is not None): require both `cosine_sim >= sim_threshold` AND `arousal >= arousal_threshold`
- **Grep results** (cosine_sim is None): filter by arousal only

| Parameter | Type | Description |
|-----------|------|-------------|
| `results` | `List[SearchResult]` | Raw search results to filter |
| `sim_threshold` | `float` | Minimum cosine similarity for semantic results |
| `arousal_threshold` | `float` | Minimum arousal for all results |

**Returns:** Filtered list of `SearchResult`.

```python
from cognitive_memory.context import filter_flashbacks

flashbacks = filter_flashbacks(response.results, sim_threshold=0.7, arousal_threshold=0.6)
```

---

## Identity

**Module:** `cognitive_memory.identity`

Read/write operations for identity markdown files (soul.md, user.md).

### `parse_identity_md(path: Path) -> dict[str, Any]`

Parse an identity markdown file into structured data.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | Path to the markdown file |

**Returns:** `{"title": str, "preamble": str, "sections": {heading: content}}`.

```python
from cognitive_memory.identity import parse_identity_md

data = parse_identity_md(Path("identity/user.md"))
print(data["sections"]["基本情報"])
```

### `write_identity_md(path: Path, data: dict[str, Any]) -> None`

Write structured data back to an identity markdown file. Creates parent directories if needed.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | Output file path |
| `data` | `dict[str, Any]` | Data dict with `title`, `preamble`, and `sections` keys |

### `update_identity_section(path: Path, section: str, content: str) -> None`

Update a single section in an identity file. Creates the file if it doesn't exist.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | Path to the identity file |
| `section` | `str` | Section heading to update or create |
| `content` | `str` | New content for the section |

```python
from cognitive_memory.identity import update_identity_section

update_identity_section(
    Path("identity/user.md"),
    "専門性",
    "- Python, TypeScript\n- AI agent design",
)
```

### `detect_placeholder_sections(path: Path) -> dict[str, bool]`

Detect which sections still contain placeholder/template content (bracket placeholders, empty fields, example-only text).

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `Path` | Path to the identity file |

**Returns:** Dict mapping section headings to `True` if the section is still a placeholder.

```python
from cognitive_memory.identity import detect_placeholder_sections

placeholders = detect_placeholder_sections(Path("identity/user.md"))
for section, is_placeholder in placeholders.items():
    if is_placeholder:
        print(f"  {section} needs real content")
```
