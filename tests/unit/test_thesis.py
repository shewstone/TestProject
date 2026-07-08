"""Unit tests for thesis generation."""

import pytest
from uuid import uuid4

from narrative_engine.models import (
    Episode,
    ArcType,
    ArcPhase,
    Thesis,
    ThesisConfidence,
    Continuation,
)
from narrative_engine.retrieval.analog_retrieval import RetrievedAnalog
from narrative_engine.thesis.generator import ThesisGenerator, AnalogEvidence


class TestThesisGenerator:
    """Tests for thesis generation."""

    def test_create_generator(self):
        """Test creating thesis generator."""
        generator = ThesisGenerator(min_analogs=2, max_analogs=5)
        assert generator.min_analogs == 2
        assert generator.max_analogs == 5

    def test_filter_analogs(self):
        """Test analog filtering."""
        generator = ThesisGenerator(min_analogs=2, confidence_threshold=0.7)

        # Create mock analogs
        episode1 = Episode(
            id=uuid4(),
            title="1929 Crash",
            summary="Stock market crash",
            arc_type=ArcType.CREDIT_BOOM_AND_BUST,
            arc_phase=ArcPhase.PANIC,
            resolution="Market bottomed",
        )

        analog1 = RetrievedAnalog(
            episode=episode1,
            semantic_similarity=0.9,
            arc_match_score=1.0,
            phase_compatibility=1.0,
            cycle_context_score=0.8,
            combined_score=0.95,
            retrieval_method="hybrid",
            reasoning="High similarity",
        )

        filtered = generator._filter_analogs([analog1])
        # Should include analog with score >= 0.7
        assert len(filtered) == 1
        assert filtered[0].combined_score == 0.95

    def test_extract_continuation(self):
        """Test extracting continuation from episode."""
        generator = ThesisGenerator()

        episode = Episode(
            id=uuid4(),
            title="Test",
            summary="Test summary",
            resolution="Crisis resolved",
            consequences=["Recovery began", "Reforms enacted"],
        )

        continuation = generator._extract_continuation(episode)
        assert "Crisis resolved" in continuation
        assert "Recovery began" in continuation

    def test_similar_continuation(self):
        """Test continuation similarity detection."""
        generator = ThesisGenerator()

        assert (
            generator._similar_continuation(
                "Market crashed and recovered", "Stock market crashed then recovered"
            )
            is True
        )

        assert generator._similar_continuation("Market crashed", "Peaceful transition") is False

    def test_generate_continuations(self):
        """Test generating continuations from evidence."""
        generator = ThesisGenerator()

        episode = Episode(
            id=uuid4(),
            title="1929 Crash",
            summary="Crash",
            resolution="Recovery within 2 years",
        )

        analog = RetrievedAnalog(
            episode=episode,
            semantic_similarity=0.9,
            arc_match_score=1.0,
            phase_compatibility=1.0,
            cycle_context_score=0.8,
            combined_score=0.9,
            retrieval_method="hybrid",
            reasoning="Similar",
        )

        evidence = [
            AnalogEvidence(
                analog=analog,
                relevance_score=0.9,
                continuation="Recovery within 2 years",
                probability_weight=0.9,
            )
        ]

        continuations = generator._generate_continuations(evidence)
        assert len(continuations) == 1
        assert continuations[0].description == "Recovery within 2 years"

    def test_calculate_confidence_high(self):
        """Test confidence calculation for strong evidence."""
        generator = ThesisGenerator(min_analogs=3)

        episode = Episode(
            id=uuid4(),
            title="Test",
            summary="Test",
            arc_type=ArcType.CREDIT_BOOM_AND_BUST,
            arc_phase=ArcPhase.PANIC,
        )

        analogs = [
            RetrievedAnalog(
                episode=episode,
                semantic_similarity=0.9,
                arc_match_score=0.9,
                phase_compatibility=0.9,
                cycle_context_score=0.9,
                combined_score=0.9,
                retrieval_method="hybrid",
                reasoning="Strong",
            )
            for _ in range(5)
        ]

        evidence = [
            AnalogEvidence(
                analog=a,
                relevance_score=0.85,
                continuation="Recovery",
                probability_weight=0.8,
            )
            for a in analogs
        ]

        continuations = [
            Continuation(description="Recovery", probability=0.8, supporting_analogs=5)
        ]

        confidence = generator._calculate_confidence(evidence, continuations)
        assert confidence in [ThesisConfidence.HIGH, ThesisConfidence.MEDIUM]


class TestAnalogEvidence:
    """Tests for analog evidence data class."""

    def test_create_evidence(self):
        """Test creating analog evidence."""
        episode = Episode(
            id=uuid4(),
            title="Test",
            summary="Test",
        )

        analog = RetrievedAnalog(
            episode=episode,
            semantic_similarity=0.8,
            arc_match_score=0.7,
            phase_compatibility=0.9,
            cycle_context_score=0.6,
            combined_score=0.75,
            retrieval_method="vector",
            reasoning="Similar arc",
        )

        evidence = AnalogEvidence(
            analog=analog,
            relevance_score=0.8,
            continuation="Market recovered",
            probability_weight=0.56,
        )

        assert evidence.relevance_score == 0.8
        assert evidence.continuation == "Market recovered"
