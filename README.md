# Cognitive Memory

[日本語](README_ja.md)

Human-like cognitive memory for AI agents — emotion-gated recall with adaptive forgetting.

Unlike traditional vector databases that treat all memories equally, Cognitive Memory models how humans actually remember: emotionally significant experiences persist longer, while routine information naturally fades. This makes AI agents feel more natural and context-aware.

## Key Features

- **Emotion-gated recall**: Arousal scores modulate memory persistence
- **Adaptive forgetting**: High-arousal memories decay slower (configurable half-life)
- **Adaptive search gate**: Skips trivial queries (greetings, acknowledgments)
- **Contextual search**: Topic-aware search with session caching and flashback filtering
- **FailOpen design**: Falls back to keyword search when embeddings are unavailable
- **Zero required dependencies**: Core uses only Python stdlib (sqlite3, urllib)
- **Pluggable embeddings**: Ollama (built-in), OpenAI, or any custom provider

## Why Cognitive Memory?

Traditional RAG and vector databases retrieve memories by semantic similarity alone. Every memory is treated equally — a casual greeting and a critical business decision have the same weight. This leads to noisy, context-poor recall that makes AI agents feel mechanical.

Cognitive Memory changes this by modeling three aspects of human cognition:

### 1. Emotion-Gated Recall

Each memory entry carries an **arousal score** (0.0–1.0) that reflects emotional intensity — surprise, insight, conflict, determination. High-arousal memories are weighted more heavily in search results.

| Query | Traditional Vector DB | Cognitive Memory |
|-------|----------------------|-----------------|
| "past pricing decisions" | Returns all mentions of "pricing" ranked by text similarity | Prioritizes the heated debate where pricing strategy was reversed (arousal: 0.9) over routine price update logs (arousal: 0.2) |

**What triggers high arousal?** Conversations with emotional or cognitive significance:

| Conversation | Arousal | Why it matters |
|---|---|---|
| "Wait, that assumption is wrong!" | 0.9 | Direction change — a premise collapsed |
| "I see, so that's how it works!" | 0.8 | Aha moment — cognitive breakthrough |
| "Let's stop this approach. Because..." | 0.7 | Rejection decision — a turning point |
| "This is the third time this topic came up" | 0.7 | Pattern recognition — metacognition |
| "Phase 1 complete" | 0.6 | Milestone — phase transition |
| "We need to investigate..." | 0.4 | Open question emerged |

These are remembered. Meanwhile, greetings ("hello"), acknowledgments ("ok"), and navigation ("let's move on") score near 0 and are skipped entirely by the adaptive search gate.

### 2. Adaptive Forgetting

Memories decay over time — but not uniformly. The decay half-life adapts to arousal:

```
half_life = base_half_life * (1 + arousal)
```

- A routine status update (arousal: 0.2) has a half-life of **72 days** and fades quickly
- A critical pivot decision (arousal: 0.9) has a half-life of **114 days** and persists far longer

This means your agent naturally "forgets" noise while retaining the moments that matter — just like human memory.

### 3. Adaptive Search Gate

Not every user message needs memory retrieval. Greetings ("hello"), acknowledgments ("ok"), and trivial messages are automatically detected and skipped, saving unnecessary embedding API calls and reducing noise in results.

### 4. Contextual Search (v0.3.1)

While basic search runs on-demand, **contextual search** automatically detects when past memories are relevant to the current conversation — and surfaces them as "flashbacks." The agent doesn't just answer your question; it recalls past experiences that add depth to the response.

**Example 1: A past decision resurfaces at the right moment**

You and the agent discussed pricing 2 weeks ago and decided to switch from per-seat to usage-based pricing after a heated debate. Today:

```
User: "Let's think about the pricing model for enterprise customers."

Agent: "For enterprise, usage-based pricing works well because it lowers
        the adoption barrier — teams can start small and scale. Key
        considerations: volume discounts above $10K/month, annual commit
        option for 15-20% discount, and a dedicated support tier..."

💭 Related past record: 2026-03-08 [DECISION] Switched from per-seat to
   usage-based pricing — per-seat penalizes large teams and creates
   resistance during expansion (arousal: 0.8)
```

Without contextual search, the agent would answer the enterprise pricing question from scratch. With it, the agent's response is grounded in the prior decision — and the flashback reminds you *why* you chose usage-based pricing in the first place.

**Example 2: A forgotten mistake prevents repeating it**

Three weeks ago, you tried to enter a market and found the timing was wrong. The memory has decayed — but its high arousal keeps it alive:

```
User: "What about expanding into the EU compliance market?"

Agent: "The EU AI Act enforcement starts Q3 2026, so there's a real
        window. Main competitors are..."

💭 Related past record: 2026-03-01 [ERROR] Regulatory timing dependency
   was too short (< 3 months lead time) — abandoned candidate after
   discovering enforcement date had shifted (arousal: 0.9)
```

The agent still answers the question directly, but the flashback acts as a gentle warning: *you've been burned by regulatory timing before.* You can choose to act on it or ignore it.

**Example 3: Trivial messages are silently skipped**

```
User: "OK"           → Gate: skipped (acknowledgment, < 1ms)
User: "Makes sense"  → Gate: skipped (short, no topic pattern)
User: "Let's analyze the competitor landscape"
                      → Gate: passes ("analyze" + topic pattern)
                      → Search executes, flashbacks shown if relevant
```

How it works:
- **Topic detection**: Recognizes new topics ("regarding...", "what about...", design/analysis keywords)
- **Session caching**: Avoids redundant embedding calls within the same conversation (cosine similarity > 0.9 = cache hit)
- **Flashback filtering**: Only surfaces results that pass both similarity (≥ 0.65) and emotional significance (arousal ≥ 0.5)
- **Performance budget**: < 200ms warm, < 1ms for gate-skipped queries

### The Result

| Aspect | Without Cognitive Memory | With Cognitive Memory |
|--------|------------------------|----------------------|
| Recall quality | All memories ranked equally by text similarity | Important memories surface first, noise fades |
| Over time | Old memories never decay, search gets noisier | Natural forgetting keeps results relevant |
| Agent personality | Generic, robotic responses | Remembers what mattered, feels more human |
| Wasted searches | Every message triggers vector search | Trivial messages are skipped automatically |
| Contextual recall | Manual search only | Past memories surface automatically when relevant |

## Install

```bash
pip install cogmem-agent
cogmem init        # Scaffolds project structure (see below)
```

`cogmem init` automatically installs the [Anthropic official skill-creator plugin](https://github.com/anthropics/claude-plugins-official) for Claude Code. This enables creating and iteratively improving skills with built-in evaluation workflows.

### Project Structure

`cogmem init` generates the following structure:

```
your-project/
├── CLAUDE.md                    # Entry point — @references only (16 lines)
├── cogmem.toml                  # Configuration
├── identity/
│   ├── agents.md                # Behavior rules (Session Init, Live Logging, Wrap, etc.)
│   ├── soul.md                  # Agent personality (role, values, thinking style)
│   └── user.md                  # User profile (auto-updated from conversations)
└── memory/
    ├── logs/                    # Session logs (YYYY-MM-DD.md)
    ├── contexts/                # Daily context files
    └── knowledge/
        ├── summary.md           # Crystallized knowledge
        └── error-patterns.md    # Recurring error patterns
```

CLAUDE.md is kept minimal — it only contains `@` references to the identity and knowledge files. All behavioral protocols live in `identity/agents.md`, making it easy to customize without touching the framework.

### Embedding Setup (recommended)

Cognitive Memory uses [Ollama](https://ollama.com/) for local embeddings. Without it, the library falls back to keyword search only.

```bash
# 1. Install Ollama (macOS)
brew install ollama

# 2. Start the server
ollama serve

# 3. Download the embedding model (~2.2 GB)
ollama pull zylonai/multilingual-e5-large
```

> Other platforms: see [ollama.com/download](https://ollama.com/download)
>
> You can also use OpenAI or any custom embedding provider — see [Embedding Providers](docs/embedding-providers.md).

### With vs Without Ollama

Cognitive Memory works in two modes depending on whether an embedding provider is available:

With Ollama, search upgrades from exact keyword matching to semantic understanding. All core Cognitive Memory features become available: related concept discovery, cross-lingual search, typo tolerance, emotion-based ranking, and adaptive forgetting. It runs entirely locally with no additional cost or privacy risk — just ~2.2 GB of disk space.

| | Without Ollama (keyword mode) | With Ollama (semantic mode) |
|---|---|---|
| **Search method** | Exact keyword matching (grep) | Vector similarity + emotion scoring |
| **"pricing strategy"** | Matches only entries containing the exact words "pricing" and "strategy" | Also finds entries about "LTV:CAC optimization", "revenue model", "cost structure" |
| **Cross-lingual** | Japanese query only matches Japanese text | "価格戦略" finds both Japanese and English entries about pricing |
| **Typos / synonyms** | "competetor analysis" returns nothing | Understands intent, returns competitor-related entries |
| **Scoring** | Binary match (found or not) | `(0.7 * cosine_sim + 0.3 * arousal) * time_decay` — nuanced ranking |
| **Adaptive forgetting** | Not available (all matches are equal) | Old low-arousal entries naturally fade from results |
| **Latency** | < 1ms | ~15ms (local, no network roundtrip) |
| **Privacy** | Local | Local — no data leaves your machine |
| **Cost** | Free | Free (Ollama is open-source) |
| **Disk usage** | 0 | ~2.2 GB (model weight) |

**Recommendation**: Install Ollama to unlock the full cognitive memory experience. The keyword fallback is designed as a safety net, not as the primary mode of operation.

## Quick Start

### CLI

```bash
cogmem init                        # Initialize project
cogmem index                       # Build/update index
cogmem search "past decisions"     # Search memories
cogmem signals                     # Check crystallization signals
cogmem context-search "query"      # Context-aware search with flashback filtering
cogmem status                      # Show statistics
cogmem migrate                     # Upgrade from older versions
```

### Python API

```python
from cognitive_memory import MemoryStore, CogMemConfig

config = CogMemConfig.from_toml("cogmem.toml")
with MemoryStore(config) as store:
    store.index_dir()
    result = store.search("past competition analysis")
    for r in result.results:
        print(f"{r.date} [{r.score:.2f}] {r.content[:80]}")
```

### Context-Aware Search (v0.3.1)

```python
from cognitive_memory import MemoryStore, SearchCache, CogMemConfig

config = CogMemConfig.from_toml("cogmem.toml")
cache = SearchCache(max_size=20, sim_threshold=0.9)

with MemoryStore(config) as store:
    store.index_dir()
    # Context search with caching and flashback filtering
    result = store.context_search(
        "pricing strategy discussion",
        cache=cache,  # Reuse across calls to avoid redundant embeds
        session_keywords=["pricing", "LTV"],
    )
    for r in result.results:
        print(f"💭 {r.date} [{r.score:.2f}] {r.content[:80]}")
```

### Convenience API

```python
from cognitive_memory import search
result = search("past decisions")  # Auto-finds cogmem.toml
```

## Scoring Formula

```
score = (0.7 * cosine_sim + 0.3 * arousal) * time_decay
```

Where `time_decay` uses an adaptive half-life:
```
half_life = base_half_life * (1 + arousal)
```

High-arousal memories (insights, conflicts, surprises) decay slower — just like human memory.

## Configuration

`cogmem.toml`:

```toml
[cogmem]
logs_dir = "memory/logs"
db_path = "memory/vectors.db"

[cogmem.identity]
soul = "identity/soul.md"
user = "identity/user.md"

[cogmem.scoring]
sim_weight = 0.7
arousal_weight = 0.3
base_half_life = 60.0
decay_floor = 0.3

[cogmem.embedding]
provider = "ollama"
model = "zylonai/multilingual-e5-large"
url = "http://localhost:11434/api/embed"
timeout = 10

[cogmem.context_search]
enabled = true
flashback_sim = 0.65        # Minimum cosine similarity for flashback
flashback_arousal = 0.5     # Minimum arousal for flashback
cache_max_size = 20         # Session cache capacity
cache_sim_threshold = 0.9   # Cache hit similarity threshold
```

### Upgrading from v0.2.0–0.2.1

```bash
pip install --upgrade cogmem-agent
cogmem migrate
```

`cogmem migrate` automatically:
- Renames `identity/agent.md` → `identity/soul.md`
- Creates `identity/agents.md` (behavioral protocols)
- Updates `cogmem.toml` and `CLAUDE.md` references

## Custom Embedding Provider

```python
class MyEmbedder:
    def embed(self, text: str) -> list[float] | None: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]] | None: ...

store = MemoryStore(config, embedder=MyEmbedder())
```

## Documentation

- [Quick Start](docs/quickstart.md)
- [Log Format](docs/log-format.md)
- [Embedding Providers](docs/embedding-providers.md)

## References

### Papers

- [NFD: Nurture-First Development](https://arxiv.org/abs/2603.10808) — Architectural framework for AI agent personality development through experiential layers and crystallization
- [A-MEM: Agentic Memory for LLM Agents](https://arxiv.org/abs/2502.12110) — Atomic note-based memory structuring for autonomous agents

### Projects

- [memory-lancedb-pro](https://github.com/mem0ai/memory-lancedb-pro) — Adaptive gate and time decay pipeline design reference
- [memU](https://github.com/NevaMind-AI/memU) — Experiential layer implementation reference
- [A-mem](https://github.com/WujiangXu/A-mem) — Atomic notes implementation reference

## License

MIT
