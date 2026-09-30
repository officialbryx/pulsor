"""Environment configuration for model training and scoring.

Kept separate from `app.config` so the `ml` package never depends on the API
layer - only `app` depends on `ml`, never the reverse.
"""
from __future__ import annotations

import os
from pathlib import Path

# Relative to the current working directory (repo root locally, `/app` in the
# container) rather than `__file__`, so the path is correct whether `ml` is
# imported from source or from an installed (non-editable) site-packages copy.
DEFAULT_MODEL_PATH = Path("models/fraud_model.joblib")


def get_model_path() -> Path:
    """Filesystem path where the trained model artifact is stored/loaded."""
    return Path(os.getenv("MODEL_PATH", str(DEFAULT_MODEL_PATH)))


def get_high_risk_threshold() -> float:
    """Risk score (0-1) at or above which a transaction is flagged as anomalous."""
    return float(os.getenv("HIGH_RISK_THRESHOLD", "0.8"))
