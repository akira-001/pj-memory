# Embedding Providers

Cognitive Memory uses a Protocol-based embedding system. Any object with `embed()` and `embed_batch()` methods works.

## Built-in: Ollama (Default)

Zero external dependencies. Uses `urllib.request` to call Ollama's API.

```toml
[cogmem.embedding]
provider = "ollama"
model = "zylonai/multilingual-e5-large"
url = "http://localhost:11434/api/embed"
timeout = 10
```

### Setup

```bash
# Install Ollama (https://ollama.ai)
ollama pull zylonai/multilingual-e5-large
```

### Recommended Models

| Model | Size | Languages | Notes |
|-------|------|-----------|-------|
| `zylonai/multilingual-e5-large` | 2.2 GB | 100+ | Best for multilingual (recommended) |
| `nomic-embed-text` | 274 MB | English | Lightweight, English-focused |
| `mxbai-embed-large` | 670 MB | English | Good quality, moderate size |

## Custom Provider

Implement two methods:

```python
from typing import List, Optional

class MyEmbedder:
    def embed(self, text: str) -> Optional[List[float]]:
        """Embed a single text. Return None on failure."""
        ...

    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Embed multiple texts. Return None on failure."""
        ...
```

Pass to MemoryStore:

```python
from cognitive_memory import MemoryStore, CogMemConfig

store = MemoryStore(config, embedder=MyEmbedder())
```

## OpenAI Provider (Example)

```bash
pip install cognitive-memory[openai]
```

```python
import openai

class OpenAIEmbedding:
    def __init__(self, model="text-embedding-3-small"):
        self.client = openai.OpenAI()
        self.model = model

    def embed(self, text):
        r = self.client.embeddings.create(input=[text], model=self.model)
        return r.data[0].embedding

    def embed_batch(self, texts):
        r = self.client.embeddings.create(input=texts, model=self.model)
        return [d.embedding for d in r.data]

store = MemoryStore(config, embedder=OpenAIEmbedding())
```

## FailOpen Behavior

If embedding fails (Ollama down, network error, etc.), Cognitive Memory falls back to keyword-based grep search. This ensures the system always returns results when possible.

Search response status indicates the mode:
- `"ok"` — Full semantic + grep search
- `"degraded (ollama_unavailable)"` — Grep only (embedding failed)
- `"degraded (no_index)"` — Grep only (no SQLite database)
- `"skipped_by_gate"` — Query too short/trivial, no search performed
