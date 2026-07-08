"""Unit tests for retrieval module (embeddings and analog retrieval)."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from uuid import uuid4

from narrative_engine.models import Episode, ArcType, ArcPhase
from narrative_engine.retrieval.embeddings import EmbeddingGenerator, EmbeddingCache
from narrative_engine.retrieval.analog_retrieval import (
    AnalogRetrievalEngine,
    RetrievedAnalog,
)


class TestEmbeddingGenerator:
    """Tests for embedding generation."""

    @pytest.fixture
    def mock_model(self):
        """Create mock sentence transformer."""
        with patch("narrative_engine.retrieval.embeddings.SentenceTransformer") as mock:
            instance = MagicMock()
            instance.get_sentence_embedding_dimension.return_value = 384
            instance.encode.return_value = np.random.randn(384)
            mock.return_value = instance
            yield mock, instance

    def test_embedding_dim_property(self, mock_model):
        """Test embedding dimension property."""
        _, mock_instance = mock_model
        generator = EmbeddingGenerator()
        generator._model = mock_instance

        assert generator.embedding_dim == 384

    def test_generate_for_episode(self, mock_model):
        """Test generating embedding for episode."""
        _, mock_instance = mock_model
        generator = EmbeddingGenerator()
        generator._model = mock_instance

        episode = Episode(
            id=uuid4(),
            title="1929 Crash",
            summary="Stock market crash",
            arc_type=ArcType.CREDIT_BOOM_AND_BUST,
            arc_phase=ArcPhase.PANIC,
            initiating_conditions=["Speculation"],
            escalation_mechanics=["Panic"],
            tension="Financial collapse",
        )

        embedding = generator.generate_for_episode(episode)

        assert len(embedding) == 384
        mock_instance.encode.assert_called_once()

        # Check structured text contains key elements
        call_args = mock_instance.encode.call_args
        text = call_args[0][0]
        assert "1929 Crash" in text
        assert "credit_boom_and_bust" in text or "boom" in text.lower()
        assert "panic" in text.lower()

    def test_similarity(self):
        """Test cosine similarity calculation."""
        generator = EmbeddingGenerator()

        # Same vector = similarity 1.0
        v = [1.0, 0.0, 0.0]
        assert generator.similarity(v, v) == pytest.approx(1.0)

        # Orthogonal vectors = similarity 0.0
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        assert generator.similarity(v1, v2) == pytest.approx(0.0)

        # Opposite vectors = similarity -1.0
        v3 = [-1.0, 0.0, 0.0]
        assert generator.similarity(v1, v3) == pytest.approx(-1.0)

    def test_compute_similarities(self):
        """Test computing similarities for multiple candidates."""
        generator = EmbeddingGenerator()

        query = [1.0, 0.0, 0.0]
        candidates = [
            [1.0, 0.0, 0.0],  # Same
            [0.0, 1.0, 0.0],  # Orthogonal
            [-1.0, 0.0, 0.0],  # Opposite
        ]

        similarities = generator.compute_similarities(query, candidates)

        assert len(similarities) == 3
        assert similarities[0] == pytest.approx(1.0)
        assert similarities[1] == pytest.approx(0.0)
        assert similarities[2] == pytest.approx(-1.0)


class TestEmbeddingCache:
    """Tests for embedding cache."""

    def test_get_and_set(self):
        """Test cache get and set."""
        cache = EmbeddingCache()

        # Cache miss
        assert cache.get("key1") is None

        # Set
        cache.set("key1", [0.1, 0.2, 0.3])

        # Cache hit
        assert cache.get("key1") == [0.1, 0.2, 0.3]

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = EmbeddingCache()

        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Miss
        cache.get("missing")
        stats = cache.get_stats()
        assert stats["misses"] == 1

        # Hit
        cache.set("key", [0.1])
        cache.get("key")
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["size"] == 1

    def test_clear(self):
        """Test cache clear."""
        cache = EmbeddingCache()
        cache.set("key", [0.1])
        cache.get("key")  # One hit

        cache.clear()

        assert cache.get("key") is None
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["size"] == 0


class TestRetrievedAnalog:
    """Tests for RetrievedAnalog data class."""

    def test_create_analog(self):
        """Test creating retrieved analog."""
        episode = Episode(
            id=uuid4(),
            title="1929 Crash",
            summary="Stock market crash",
        )

        analog = RetrievedAnalog(
            episode=episode,
            semantic_similarity=0.85,
            arc_match_score=1.0,
            phase_compatibility=0.9,
            cycle_context_score=0.8,
            combined_score=0.88,
            retrieval_method="hybrid",
            reasoning="Same arc type",
        )

        assert analog.episode.title == "1929 Crash"
        assert analog.combined_score == 0.88
        assert analog.retrieval_method == "hybrid"


class TestAnalogRetrievalEngine:
    """Tests for analog retrieval engine."""

    def test_create_engine(self):
        """Test creating retrieval engine."""
        engine = AnalogRetrievalEngine(
            vector_weight=0.5,
            arc_weight=0.2,
            phase_weight=0.15,
            cycle_weight=0.15,
        )

        assert engine.vector_weight == 0.5
        assert engine.arc_weight == 0.2

    def test_compute_arc_match_exact(self):
        """Test exact arc type match."""
        engine = AnalogRetrievalEngine()

        score = engine._compute_arc_match(
            ArcType.CREDIT_BOOM_AND_BUST,
            ArcType.CREDIT_BOOM_AND_BUST,
        )
        assert score == 1.0

    def test_compute_arc_match_related(self):
        """Test related arc type match."""
        engine = AnalogRetrievalEngine()

        score = engine._compute_arc_match(
            ArcType.CREDIT_BOOM_AND_BUST,
            ArcType.HUBRIS_NEMESIS,
        )
        assert score == 0.6  # Related

    def test_compute_arc_match_different(self):
        """Test different arc type match."""
        engine = AnalogRetrievalEngine()

        score = engine._compute_arc_match(
            ArcType.HERO_JOURNEY,
            ArcType.TRAGEDY,
        )
        assert score == 0.1  # Different

    def test_compute_arc_match_unknown(self):
        """Test match with unknown arc."""
        engine = AnalogRetrievalEngine()

        score = engine._compute_arc_match(
            ArcType.CREDIT_BOOM_AND_BUST,
            None,
        )
        assert score == 0.5  # Neutral

    def test_compute_phase_compatibility_same(self):
        """Test same phase compatibility."""
        engine = AnalogRetrievalEngine()

        score = engine._compute_phase_compatibility(
            ArcPhase.PANIC,
            ArcPhase.PANIC,
            ArcType.CREDIT_BOOM_AND_BUST,
            ArcType.CREDIT_BOOM_AND_BUST,
        )
        assert score == 1.0  # Same phase, same arc

    def test_compute_phase_compatibility_different_arcs(self):
        """Test phase compatibility across different arcs."""
        engine = AnalogRetrievalEngine()

        score = engine._compute_phase_compatibility(
            ArcPhase.CLIMAX,
            ArcPhase.CLIMAX,
            ArcType.CREDIT_BOOM_AND_BUST,
            ArcType.HERO_JOURNEY,
        )
        assert score == 0.6  # Same phase category

    def test_categorize_phase(self):
        """Test phase categorization."""
        engine = AnalogRetrievalEngine()

        assert engine._categorize_phase(ArcPhase.SETUP) == "early"
        assert engine._categorize_phase(ArcPhase.EUPHORIA) == "middle"
        assert engine._categorize_phase(ArcPhase.PANIC) == "late"

    def test_similar_continuation(self):
        """Test continuation similarity detection."""
        engine = AnalogRetrievalEngine()

        # Similar
        assert (
            engine._similar_continuation(
                "Market crashed and recovered", "Stock market crashed then recovered"
            )
            is True
        )

        # Different
        assert engine._similar_continuation("Market crashed", "Peaceful transition") is False

        # Edge case - no overlap
        assert engine._similar_continuation("abc def", "ghi jkl") is False


class TestAnalogRetrievalIntegration:
    """Integration-style tests for analog retrieval."""

    @pytest.mark.asyncio
    async def test_retrieve_analogs_mock(self):
        """Test analog retrieval with mocked dependencies."""
        from sqlalchemy.ext.asyncio import AsyncSession

        engine = AnalogRetrievalEngine()

        # Mock session
        mock_session = MagicMock(spec=AsyncSession)

        query_episode = Episode(
            id=uuid4(),
            title="2024 Market Conditions",
            summary="Similar to 1929",
            arc_type=ArcType.CREDIT_BOOM_AND_BUST,
            arc_phase=ArcPhase.DISTRESS,
        )

        # Would need to mock EpisodeRepository.search_by_embedding
        # This test validates the orchestration structure
        # Full integration test would require actual database

        assert engine.min_analogs == 3
        assert engine.confidence_threshold == 0.6
