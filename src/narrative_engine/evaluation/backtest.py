"""Backtesting framework for historical forecast validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import UUID

import structlog

from narrative_engine.evaluation.metrics import BrierScore
from narrative_engine.models import Episode, Thesis, ThesisConfidence

logger = structlog.get_logger()


@dataclass
class BacktestResult:
    """Result of backtesting a thesis against historical data."""

    thesis_id: UUID
    query_date: datetime
    resolution_date: datetime

    # Predictions
    predicted_continuation: str
    predicted_probability: float
    confidence: ThesisConfidence

    # Actual outcome
    actual_outcome: str
    outcome_matched: bool

    # Metrics
    brier_score: float
    accuracy: str  # "accurate", "partial", "miss"

    # Analysis
    missed_factors: List[str] = field(default_factory=list)
    lessons: str = ""


class BacktestEngine:
    """Engine for backtesting thesis forecasts."""

    def __init__(self) -> None:
        self.logger = structlog.get_logger()

    def run_backtest(
        self,
        thesis: Thesis,
        actual_outcome: str,
        resolution_date: datetime,
    ) -> BacktestResult:
        """Run backtest for a single thesis.

        Compares predicted continuation against actual outcome.
        """
        self.logger.info(
            "Running backtest",
            thesis_id=str(thesis.id),
            query_date=thesis.query_date.isoformat(),
        )

        # Find which continuation was predicted
        predicted = thesis.dominant_continuation.description
        predicted_prob = thesis.dominant_continuation.probability

        # Check if actual outcome matches any prediction
        all_continuations = [thesis.dominant_continuation.description]
        all_continuations.extend([c[0] for c in thesis.alternative_continuations])

        matched, match_idx = self._match_outcome(actual_outcome, all_continuations)

        # Calculate Brier score
        if matched:
            if match_idx == 0:
                brier = BrierScore.calculate(predicted_prob, 1)
                accuracy = "accurate"
            else:
                # Matched an alternative
                alt_prob = thesis.alternative_continuations[match_idx - 1][1]
                brier = BrierScore.calculate(alt_prob, 1)
                accuracy = "partial"
        else:
            brier = BrierScore.calculate(predicted_prob, 0)
            accuracy = "miss"

        # Identify missed factors
        missed_factors = self._identify_missed_factors(thesis, actual_outcome)

        result = BacktestResult(
            thesis_id=thesis.id,
            query_date=thesis.query_date,
            resolution_date=resolution_date,
            predicted_continuation=predicted,
            predicted_probability=predicted_prob,
            confidence=thesis.confidence,
            actual_outcome=actual_outcome,
            outcome_matched=matched,
            brier_score=brier.score,
            accuracy=accuracy,
            missed_factors=missed_factors,
            lessons=self._generate_lessons(thesis, matched, missed_factors),
        )

        self.logger.info(
            "Backtest complete",
            brier_score=result.brier_score,
            accuracy=result.accuracy,
        )

        return result

    def _match_outcome(
        self,
        actual: str,
        predictions: List[str],
    ) -> Tuple[bool, int]:
        """Check if actual outcome matches any prediction.

        Returns (matched, index_of_match)
        """
        actual_lower = actual.lower()
        actual_words = set(actual_lower.split())

        for i, pred in enumerate(predictions):
            pred_lower = pred.lower()
            pred_words = set(pred_lower.split())

            overlap = len(actual_words & pred_words)
            min_len = min(len(actual_words), len(pred_words))

            if overlap >= 2 or (min_len > 0 and overlap / min_len >= 0.3):
                return True, i

        return False, -1

    def _identify_missed_factors(
        self,
        thesis: Thesis,
        actual_outcome: str,
    ) -> List[str]:
        """Identify factors that were missed in the forecast."""
        factors = []

        # Check watch conditions
        actual_lower = actual_outcome.lower()

        for indicator in thesis.watch_conditions:
            if indicator.lower() not in actual_lower:
                factors.append(f"Missed indicator: {indicator}")

        # Check uncertainties
        for uncertainty in thesis.key_uncertainties:
            if uncertainty.lower() in actual_lower:
                factors.append(f"Realized uncertainty: {uncertainty}")

        return factors[:5]  # Limit to top 5

    def _generate_lessons(
        self,
        thesis: Thesis,
        matched: bool,
        missed_factors: List[str],
    ) -> str:
        """Generate lessons learned from backtest."""
        if matched:
            if thesis.confidence == ThesisConfidence.HIGH:
                return "High confidence with accurate prediction validates methodology"
            else:
                return "Prediction accurate despite lower confidence"
        else:
            if missed_factors:
                return f"Missed {len(missed_factors)} key factors: " + ", ".join(missed_factors[:2])
            else:
                return "Outcome was outside predicted distribution"

    def batch_backtest(
        self,
        theses: List[Thesis],
        outcomes: Dict[UUID, Tuple[str, datetime]],  # thesis_id -> (outcome, date)
    ) -> List[BacktestResult]:
        """Run backtest on multiple theses."""
        results = []

        for thesis in theses:
            if thesis.id in outcomes:
                outcome, date = outcomes[thesis.id]
                result = self.run_backtest(thesis, outcome, date)
                results.append(result)

        return results

    def compute_summary_stats(
        self,
        results: List[BacktestResult],
    ) -> dict:
        """Compute summary statistics from backtest results."""
        if not results:
            return {}

        total = len(results)
        accurate = sum(1 for r in results if r.accuracy == "accurate")
        partial = sum(1 for r in results if r.accuracy == "partial")
        miss = sum(1 for r in results if r.accuracy == "miss")

        avg_brier = sum(r.brier_score for r in results) / total

        by_confidence = {}
        for conf in ThesisConfidence:
            conf_results = [r for r in results if r.confidence == conf]
            if conf_results:
                by_confidence[conf.value] = {
                    "count": len(conf_results),
                    "avg_brier": sum(r.brier_score for r in conf_results) / len(conf_results),
                    "accuracy": sum(1 for r in conf_results if r.outcome_matched) / len(conf_results),
                }

        return {
            "total": total,
            "accurate": accurate,
            "partial": partial,
            "miss": miss,
            "accuracy_rate": (accurate + partial * 0.5) / total,
            "avg_brier_score": avg_brier,
            "by_confidence": by_confidence,
        }


class HistoricalDataset:
    """Dataset of historical episodes with known outcomes for backtesting."""

    def __init__(self) -> None:
        self.episodes: List[Episode] = []
        self.outcomes: Dict[UUID, str] = {}

    def add_episode(
        self,
        episode: Episode,
        outcome: str,
    ) -> None:
        """Add episode with known outcome."""
        self.episodes.append(episode)
        self.outcomes[episode.id] = outcome

    def get_train_test_split(
        self,
        test_ratio: float = 0.2,
    ) -> Tuple[List[Episode], List[Episode]]:
        """Split dataset for cross-validation."""
        import random

        shuffled = self.episodes.copy()
        random.shuffle(shuffled)

        split_idx = int(len(shuffled) * (1 - test_ratio))
        return shuffled[:split_idx], shuffled[split_idx:]

    def evaluate_prediction(
        self,
        query: Episode,
        prediction: str,
    ) -> bool:
        """Check if prediction matches actual outcome."""
        if query.id in self.outcomes:
            return self._similar_outcome(prediction, self.outcomes[query.id])
        return False

    def _similar_outcome(self, a: str, b: str) -> bool:
        """Check if two outcomes are similar."""
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        overlap = len(a_words & b_words)
        return overlap >= 2
