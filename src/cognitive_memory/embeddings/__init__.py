"""Embedding providers for Cognitive Memory."""

from ._protocol import EmbeddingProvider
from .ollama import OllamaEmbedding

__all__ = ["EmbeddingProvider", "OllamaEmbedding"]
