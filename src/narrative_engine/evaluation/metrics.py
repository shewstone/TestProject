"""Evaluation metrics for thesis forecasts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from narrative_engine.models import Thesis, ThesisConfidence


@dataclass
class BrierScore:
    """Brier score for probabilistic forecast evaluation."""

    score: float  # 0.0 (perfect) to 1.0 (worst)
    probability: float  # Predicted probability
    outcome: int  # 1 if occurred, 0 if not

    @classmethod
    def calculate(cls, probability: float, outcome: int) -> "BrierScore":
        """Calculate Brier score.

        Brier score = (probability - outcome)²

        Single-probability binary convention: 0.0 is perfect, 1.0 is the
        worst (100% confidence in the wrong outcome). (The original
        two-category sum convention doubles this; everything in this
        codebase uses the 0-1 form.)
        """
        if not 0 <= probability <= 1:
            raise ValueError("Probability must be between 0 and 1")
        if outcome not in (0, 1):
            raise ValueError("Outcome must be 0 or 1")

        score = (probability - outcome) ** 2
        return cls(score=score, probability=probability, outcome=outcome)

    @property
    def is_accurate(self) -> bool:
        """Return True if forecast was directionally accurate."""
        if self.outcome == 1:
            return self.probability >= 0.5
        return self.probability < 0.5


@dataclass
class CalibrationPoint:
    """Single calibration bin result."""

    bin_range: Tuple[float, float]  # (min_prob, max_prob)
    predicted: float  # Average predicted probability in bin
    observed: float  # Actual frequency in bin
    count: int  # Number of forecasts in bin

    @property
    def calibration_error(self) -> float:
        """Difference between predicted and observed."""
        return abs(self.predicted - self.observed)


class CalibrationAnalyzer:
    """Analyze forecast calibration."""

    def __init__(self, num_bins: int = 10) -> None:
        self.num_bins = num_bins

    def analyze(
        self,
        forecasts: List[Tuple[float, int]],  # (probability, outcome) pairs
    ) -> List[CalibrationPoint]:
        """Compute calibration bins.

        Groups forecasts by predicted probability and compares
        to actual outcome frequency.
        """
        # Initialize bins
        bins: List[List[Tuple[float, int]]] = [[] for _ in range(self.num_bins)]
        bin_size = 1.0 / self.num_bins

        # Assign forecasts to bins
        for prob, outcome in forecasts:
            bin_idx = min(int(prob / bin_size), self.num_bins - 1)
            bins[bin_idx].append((prob, outcome))

        # Compute calibration points
        points = []
        for i, bin_forecasts in enumerate(bins):
            bin_min = i * bin_size
            bin_max = (i + 1) * bin_size

            if not bin_forecasts:
                points.append(
                    CalibrationPoint(
                        bin_range=(bin_min, bin_max),
                        predicted=(bin_min + bin_max) / 2,
                        observed=0.0,
                        count=0,
                    )
                )
            else:
                avg_predicted = sum(f[0] for f in bin_forecasts) / len(bin_forecasts)
                observed_freq = sum(f[1] for f in bin_forecasts) / len(bin_forecasts)

                points.append(
                    CalibrationPoint(
                        bin_range=(bin_min, bin_max),
                        predicted=avg_predicted,
                        observed=observed_freq,
                        count=len(bin_forecasts),
                    )
                )

        return points

    def expected_calibration_error(
        self,
        calibration_points: List[CalibrationPoint],
    ) -> float:
        """Compute Expected Calibration Error (ECE)."""
        total = sum(p.count for p in calibration_points)
        if total == 0:
            return 0.0

        return sum(p.calibration_error * p.count / total for p in calibration_points)


class ThesisEvaluator:
    """Evaluate thesis forecasts against actual outcomes."""

    def evaluate_thesis(
        self,
        thesis: Thesis,
        actual_outcome: str,
    ) -> Tuple[BrierScore, str]:
        """Evaluate a single thesis against actual outcome.

        Returns Brier score and matched continuation.
        """
        # Find which predicted continuation matches actual outcome
        all_continuations = [(thesis.dominant_continuation.description, thesis.dominant_continuation.probability)]
        all_continuations.extend(thesis.alternative_continuations)

        # Simple matching: check if actual outcome is close to any prediction
        matched_idx = self._find_match(actual_outcome, [c[0] for c in all_continuations])

        if matched_idx == 0:
            prob = all_continuations[0][1]
            brier = BrierScore.calculate(prob, 1)
            return brier, "dominant"
        elif matched_idx > 0:
            prob = all_continuations[matched_idx][1]
            brier = BrierScore.calculate(prob, 1)
            return brier, "alternative"
        else:
            # No match - assume dominant was predicted
            brier = BrierScore.calculate(all_continuations[0][1], 0)
            return brier, "miss"

    def _find_match(
        self,
        actual: str,
        predictions: List[str],
    ) -> int:
        """Find which prediction matches actual outcome.

        Returns index of match or -1 if none.
        """
        actual_lower = actual.lower()

        for i, pred in enumerate(predictions):
            # Simple keyword matching
            pred_lower = pred.lower()

            # Check for significant word overlap
            actual_words = set(actual_lower.split())
            pred_words = set(pred_lower.split())

            overlap = len(actual_words & pred_words)
            min_words = min(len(actual_words), len(pred_words))

            if overlap >= 2 or (min_words > 0 and overlap / min_words >= 0.5):
                return i

        return -1

    def confidence_accuracy(
        self,
        theses: List[Thesis],
    ) -> dict:
        """Compute accuracy by confidence level."""
        by_confidence: dict = {
            ThesisConfidence.HIGH: {"correct": 0, "total": 0},
            ThesisConfidence.MEDIUM: {"correct": 0, "total": 0},
            ThesisConfidence.LOW: {"correct": 0, "total": 0},
            ThesisConfidence.UNKNOWN: {"correct": 0, "total": 0},
        }

        for _thesis in theses:
            # Would need actual outcome to compute accuracy
            # Placeholder for structure
            pass

        return by_confidence


def compute_skill_score(
    actual_brier: float,
    reference_brier: float,
) -> float:
    """Compute skill score vs reference forecast.

    Skill = 1 - (BS_actual / BS_reference)

    Positive = better than reference
    Zero = same as reference
    Negative = worse than reference
    """
    if reference_brier == 0:
        return 0.0
    return 1.0 - (actual_brier / reference_brier)
