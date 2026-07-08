"""Retrieval layer for analog finding.

Vector search and analog retrieval.
"""

from narrative_engine.retrieval.analog_retrieval import AnalogRetriever
from narrative_engine.retrieval.embeddings import EmbeddingGenerator

__all__ = [
    "AnalogRetriever",
    "EmbeddingGenerator",
]
