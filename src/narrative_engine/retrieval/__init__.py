"""Retrieval layer for analog finding.

Vector search and analog retrieval.
"""

from narrative_engine.retrieval.analog_retrieval import AnalogRetrievalEngine, RetrievedAnalog
from narrative_engine.retrieval.embeddings import EmbeddingGenerator

# Alias for backwards compatibility
AnalogRetriever = AnalogRetrievalEngine

__all__ = [
    "AnalogRetrievalEngine",
    "AnalogRetriever",
    "RetrievedAnalog",
    "EmbeddingGenerator",
]
