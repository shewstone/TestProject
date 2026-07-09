"""Unit tests for analog retrieval scoring helpers."""

from narrative_engine.models import MechanismTag
from narrative_engine.retrieval.analog_retrieval import AnalogRetrievalEngine


class TestMechanismOverlap:
    """Tests for mechanism-tag overlap scoring (design doc Sec 3.8)."""

    def test_no_tags_is_neutral(self):
        engine = AnalogRetrievalEngine()
        assert engine._compute_mechanism_overlap([], []) == 0.5
        assert (
            engine._compute_mechanism_overlap([MechanismTag.CREDIT_EXPANSION], []) == 0.5
        )

    def test_identical_tags_score_one(self):
        engine = AnalogRetrievalEngine()
        tags = [MechanismTag.CREDIT_EXPANSION, MechanismTag.ASSET_BUBBLE]
        assert engine._compute_mechanism_overlap(tags, tags) == 1.0

    def test_partial_overlap_is_jaccard(self):
        engine = AnalogRetrievalEngine()
        query = [MechanismTag.CREDIT_EXPANSION, MechanismTag.ASSET_BUBBLE]
        candidate = [MechanismTag.CREDIT_EXPANSION, MechanismTag.FISCAL_DISTRESS]
        # shared={CREDIT_EXPANSION}, union has 3 -> 1/3
        assert engine._compute_mechanism_overlap(query, candidate) == 1 / 3

    def test_disjoint_tags_score_zero(self):
        engine = AnalogRetrievalEngine()
        query = [MechanismTag.CREDIT_EXPANSION]
        candidate = [MechanismTag.FISCAL_DISTRESS]
        assert engine._compute_mechanism_overlap(query, candidate) == 0.0
