"""Feature engineering shared by training and online inference.

Keeping this transform in one place guarantees training and serving can
never drift apart (a common source of real-world model bugs).
"""
from __future__ import annotations

from datetime import timezone

import numpy as np
import pandas as pd

FEATURE_NAMES = ["log_amount", "hour", "merchant_risk", "country_risk"]

# Illustrative risk priors for common merchant categories / countries. In a
# production system these would come from a feature store built on historical
# chargeback and SAR (suspicious activity report) data.
MERCHANT_RISK: dict[str, float] = {
    "groceries": 0.05,
    "food": 0.05,
    "retail": 0.1,
    "travel": 0.2,
    "electronics": 0.25,
    "cryptocurrency": 0.9,
    "gambling": 0.85,
    "wire_transfer": 0.8,
    "cash_advance": 0.8,
}
DEFAULT_MERCHANT_RISK = 0.65

COUNTRY_RISK: dict[str, float] = {"US": 0.05, "CA": 0.05, "GB": 0.05, "AU": 0.1}
DEFAULT_COUNTRY_RISK = 0.55


def transform(transaction: dict) -> pd.DataFrame:
    """Convert a raw transaction payload into the model's numeric feature frame."""
    timestamp = transaction["timestamp"]
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    category = transaction["merchant_category"].strip().lower()
    country = transaction["country"].strip().upper()
    return pd.DataFrame(
        [
            {
                "log_amount": np.log1p(transaction["amount"]),
                "hour": timestamp.hour,
                "merchant_risk": MERCHANT_RISK.get(category, DEFAULT_MERCHANT_RISK),
                "country_risk": COUNTRY_RISK.get(country, DEFAULT_COUNTRY_RISK),
            }
        ],
        columns=FEATURE_NAMES,
    )
