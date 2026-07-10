"""Unit tests for evaluation metrics and backtesting."""

from datetime import datetime
from uuid import uuid4

import pytest

from narrative_engine.evaluation.backtest import (
    BacktestEngine,
    BacktestResult,
    HistoricalDataset,
)
from narrative_engine.evaluation.metrics import (
    BrierScore,
    CalibrationAnalyzer,
    CalibrationPoint,
    compute_skill_score,
)
from narrative_engine.models import Continuation, Thesis, ThesisConfidence


class TestBrierScore:
    """Tests for Brier score calculation."""

    def test_perfect_prediction(self):
        """Test perfect prediction (0.0 Brier score)."""
        score = BrierScore.calculate(probability=1.0, outcome=1)
        assert score.score == 0.0
        assert score.is_accurate is True

    def test_perfect_rejection(self):
        """Test perfect rejection (0.0 Brier score)."""
        score = BrierScore.calculate(probability=0.0, outcome=0)
        assert score.score == 0.0
        assert score.is_accurate is True

    def test_worst_prediction(self):
        """Test worst prediction (1.0 Brier score)."""
        score = BrierScore.calculate(probability=1.0, outcome=0)
        assert score.score == 1.0
        assert score.is_accurate is False

    def test_uncertain_correct(self):
        """Test uncertain but correct prediction."""
        score = BrierScore.calculate(probability=0.6, outcome=1)
        assert score.score == pytest.approx(0.16)
        assert score.is_accurate is True

    def test_uncertain_wrong(self):
        """Test uncertain and wrong prediction."""
        score = BrierScore.calculate(probability=0.6, outcome=0)
        assert score.score == pytest.approx(0.36)
        assert score.is_accurate is False

    def test_invalid_probability(self):
        """Test invalid probability raises error."""
        with pytest.raises(ValueError):
            BrierScore.calculate(probability=1.5, outcome=1)

    def test_invalid_outcome(self):
        """Test invalid outcome raises error."""
        with pytest.raises(ValueError):
            BrierScore.calculate(probability=0.5, outcome=2)


class TestCalibrationAnalyzer:
    """Tests for calibration analysis."""

    def test_perfect_calibration(self):
        """Test perfect calibration."""
        analyzer = CalibrationAnalyzer(num_bins=10)

        # Forecasts that perfectly match their probability bins
        forecasts = []
        for i in range(100):
            prob = 0.5
            outcome = 1 if i < 50 else 0  # 50% actual frequency
            forecasts.append((prob, outcome))

        points = analyzer.analyze(forecasts)

        # Check middle bin
        mid_bin = points[5]  # 0.5 probability bin
        assert mid_bin.predicted == pytest.approx(0.5, abs=0.1)
        assert mid_bin.observed == pytest.approx(0.5, abs=0.1)

    def test_overconfident_calibration(self):
        """Test overconfident forecasts."""
        analyzer = CalibrationAnalyzer(num_bins=10)

        # Predict 90% but only 50% occur
        forecasts = [(0.9, 1) for _ in range(50)] + [(0.9, 0) for _ in range(50)]

        points = analyzer.analyze(forecasts)

        # High probability bin should show calibration error
        high_bin = points[8]  # 0.8-0.9 bin
        if high_bin.count > 0:
            assert high_bin.predicted > high_bin.observed  # Overconfident

    def test_ece_calculation(self):
        """Test Expected Calibration Error calculation."""
        analyzer = CalibrationAnalyzer(num_bins=10)

        points = [
            CalibrationPoint((0.0, 0.1), 0.05, 0.05, 100),  # Perfect
            CalibrationPoint((0.9, 1.0), 0.95, 0.5, 100),  # Large error
        ]

        ece = analyzer.expected_calibration_error(points)

        # ECE should be weighted average of errors
        # (0.0 * 100 + 0.45 * 100) / 200 = 0.225
        assert ece == pytest.approx(0.225, abs=0.05)


class TestBacktestEngine:
    """Tests for backtest engine."""

    @pytest.fixture
    def sample_thesis(self):
        """Create sample thesis for testing."""
        return Thesis(
            id=uuid4(),
            query="Will market crash?",
            query_date=datetime(2024, 1, 1),
            dominant_continuation=Continuation(
                description="Market crashes",
                probability=0.7,
            ),
            alternative_continuations=[
                ("Soft landing", 0.2),
                ("Continues up", 0.1),
            ],
            confidence=ThesisConfidence.HIGH,
            watch_for_indicators=["High leverage", "Inverted yield curve"],
            key_uncertainties=["Fed policy"],
            model_version="thesis-v1.0",
            taxonomy_version="arc-v0.1.0",
        )

    def test_accurate_prediction(self, sample_thesis):
        """Test accurate prediction backtest."""
        engine = BacktestEngine()

        result = engine.run_backtest(
            thesis=sample_thesis,
            actual_outcome="Market crashed significantly",
            resolution_date=datetime(2024, 6, 1),
        )

        assert result.outcome_matched is True
        assert result.accuracy == "accurate"
        assert result.brier_score == pytest.approx(0.09, abs=0.01)  # (0.7-1)²

    def test_missed_prediction(self, sample_thesis):
        """Test missed prediction backtest."""
        engine = BacktestEngine()

        result = engine.run_backtest(
            thesis=sample_thesis,
            actual_outcome="Soft landing achieved",
            resolution_date=datetime(2024, 6, 1),
        )

        assert result.outcome_matched is True
        assert result.accuracy == "partial"  # Matched alternative

    def test_complete_miss(self, sample_thesis):
        """Test complete miss backtest."""
        engine = BacktestEngine()

        result = engine.run_backtest(
            thesis=sample_thesis,
            actual_outcome="Unexpected innovation boom",
            resolution_date=datetime(2024, 6, 1),
        )

        assert result.outcome_matched is False
        assert result.accuracy == "miss"
        assert result.brier_score == pytest.approx(0.49, abs=0.01)  # (0.7-0)²

    def test_match_outcome(self):
        """Test outcome matching logic."""
        engine = BacktestEngine()

        matched, idx = engine._match_outcome("Market crashed", ["Market crashes", "Soft landing"])
        assert matched is True
        assert idx == 0

        matched, idx = engine._match_outcome("Peaceful transition", ["Market crashes", "Soft landing"])
        assert matched is False
        assert idx == -1

    def test_summary_stats(self):
        """Test summary statistics computation."""
        engine = BacktestEngine()

        results = [
            BacktestResult(
                thesis_id=uuid4(),
                query_date=datetime(2024, 1, 1),
                resolution_date=datetime(2024, 6, 1),
                predicted_continuation="Crash",
                predicted_probability=0.8,
                confidence=ThesisConfidence.HIGH,
                actual_outcome="Crashed",
                outcome_matched=True,
                brier_score=0.04,
                accuracy="accurate",
            ),
            BacktestResult(
                thesis_id=uuid4(),
                query_date=datetime(2024, 1, 1),
                resolution_date=datetime(2024, 6, 1),
                predicted_continuation="Crash",
                predicted_probability=0.7,
                confidence=ThesisConfidence.MEDIUM,
                actual_outcome="Rose",
                outcome_matched=False,
                brier_score=0.49,
                accuracy="miss",
            ),
        ]

        stats = engine.compute_summary_stats(results)

        assert stats["total"] == 2
        assert stats["accurate"] == 1
        assert stats["miss"] == 1
        assert stats["accuracy_rate"] == 0.5
        assert stats["avg_brier_score"] == pytest.approx(0.265, abs=0.01)


class TestHistoricalDataset:
    """Tests for historical dataset."""

    def test_add_episode(self):
        """Test adding episode to dataset."""
        from narrative_engine.models import Episode

        dataset = HistoricalDataset()
        episode = Episode(
            id=uuid4(),
            title="1929 Crash",
            summary="Stock market crash",
        )

        dataset.add_episode(episode, "Severe depression followed")

        assert len(dataset.episodes) == 1
        assert episode.id in dataset.outcomes

    def test_train_test_split(self):
        """Test train/test split."""
        from narrative_engine.models import Episode

        dataset = HistoricalDataset()

        for i in range(10):
            dataset.add_episode(Episode(id=uuid4(), title=f"Episode {i}", summary="Test"), "Outcome")

        train, test = dataset.get_train_test_split(test_ratio=0.3)

        assert len(train) == 7
        assert len(test) == 3

    def test_evaluate_prediction(self):
        """Test prediction evaluation."""
        from narrative_engine.models import Episode

        dataset = HistoricalDataset()
        episode = Episode(id=uuid4(), title="Test", summary="Test")
        dataset.add_episode(episode, "Market crashed")

        assert dataset.evaluate_prediction(episode, "Market crashes") is True
        assert dataset.evaluate_prediction(episode, "Peaceful landing") is False


class TestSkillScore:
    """Tests for skill score computation."""

    def test_better_than_reference(self):
        """Test skill score when better than reference."""
        score = compute_skill_score(actual_brier=0.1, reference_brier=0.3)
        assert score > 0
        assert score == pytest.approx(0.667, abs=0.01)

    def test_worse_than_reference(self):
        """Test skill score when worse than reference."""
        score = compute_skill_score(actual_brier=0.4, reference_brier=0.2)
        assert score < 0
        assert score == pytest.approx(-1.0, abs=0.01)

    def test_same_as_reference(self):
        """Test skill score when same as reference."""
        score = compute_skill_score(actual_brier=0.2, reference_brier=0.2)
        assert score == 0.0

    def test_zero_reference(self):
        """Test skill score with zero reference."""
        score = compute_skill_score(actual_brier=0.1, reference_brier=0.0)
        assert score == 0.0  # Avoids division by zero
