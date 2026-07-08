"""Evaluation and backtesting framework.

Brier scores, calibration, and masked-ending tests.
"""

from narrative_engine.evaluation.backtest import (
    BacktestEngine,
    HistoricalDataset,
)
from narrative_engine.evaluation.metrics import (
    BrierScore,
    CalibrationAnalyzer,
)

__all__ = [
    "BacktestEngine",
    "HistoricalDataset",
    "BrierScore",
    "CalibrationAnalyzer",
]
