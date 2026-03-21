# Cognitive Memory

Human-like cognitive memory for AI agents — emotion-gated recall with adaptive forgetting.

Unlike traditional vector databases that treat all memories equally, Cognitive Memory models how humans actually remember: emotionally significant experiences persist longer, while routine information naturally fades. This makes AI agents feel more natural and context-aware.

## Key Features

- **Emotion-gated recall**: Arousal scores modulate memory persistence
- **Adaptive forgetting**: High-arousal memories decay slower (configurable half-life)
- **Adaptive search gate**: Skips trivial queries (greetings, acknowledgments)
- **FailOpen design**: Falls back to keyword search when embeddings are unavailable
- **Zero required dependencies**: Core uses only Python stdlib (sqlite3, urllib)
- **Pluggable embeddings**: Ollama (built-in), OpenAI, or any custom provider

## Install

```bash
pip install cognitive-memory
```

## Quick Start

### CLI

```bash
cogmem init                        # Initialize project
cogmem index                       # Build/update index
cogmem search "past decisions"     # Search memories
cogmem status                      # Show statistics
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
```

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

## License

MIT
