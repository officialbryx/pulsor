"""Synthetic transaction data generation used for training, tests, and demos.

FraudPulse ships without access to real payment data, so every model in this
project is trained on synthetic transactions. The generators below encode the
same domain assumptions as `ml.features` (merchant/country risk tables) so
the training distribution matches what the API sees at inference time.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from ml.features import COUNTRY_RISK, FEATURE_NAMES, MERCHANT_RISK


def generate_feature_frame(size: int = 1000, seed: int = 42) -> pd.DataFrame:
    """Unlabeled feature samples used to fit the unsupervised anomaly model."""
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "log_amount": np.log1p(rng.lognormal(mean=4, sigma=1, size=size)),
            "hour": np.clip(rng.normal(loc=13, scale=4, size=size), 0, 23),
            "merchant_risk": rng.choice([0.05, 0.1, 0.2, 0.25], size=size),
            "country_risk": rng.choice([0.05, 0.1], size=size),
        }
    )
    return frame[FEATURE_NAMES]


def generate_labeled_dataset(
    size: int = 4000, fraud_rate: float = 0.06, seed: int = 42
) -> tuple[pd.DataFrame, pd.Series]:
    """Labeled samples used to fit the supervised fraud classifier.

    Labels come from a noisy weighted combination of risk signals rather than
    hard rules, so the classifier has to learn a soft decision boundary
    instead of memorizing the rule-based `risk_factors` checks in `ml.model`.
    """
    rng = np.random.default_rng(seed)
    log_amount = np.log1p(rng.lognormal(mean=4, sigma=1.1, size=size))
    hour = np.clip(rng.normal(loc=13, scale=5, size=size), 0, 23)
    merchant_risk = rng.choice(sorted(set(MERCHANT_RISK.values())), size=size)
    country_risk = rng.choice(sorted(set(COUNTRY_RISK.values())) + [0.55], size=size)

    z_amount = (log_amount - log_amount.mean()) / log_amount.std()
    unusual_hour = ((hour < 5) | (hour > 23)).astype(float)
    signal = (
        0.35 * z_amount
        + 0.30 * merchant_risk
        + 0.20 * country_risk
        + 0.15 * unusual_hour
        + rng.normal(scale=0.15, size=size)
    )
    threshold = np.quantile(signal, 1 - fraud_rate)
    label = pd.Series((signal >= threshold).astype(int), name="is_fraud")

    features = pd.DataFrame(
        {
            "log_amount": log_amount,
            "hour": hour,
            "merchant_risk": merchant_risk,
            "country_risk": country_risk,
        }
    )[FEATURE_NAMES]
    return features, label


# A small, realistic mix used to seed `data/sample_transactions.json` and the
# demo client. Countries outside `COUNTRY_RISK` (e.g. "NG", "RU", "KY")
# intentionally fall back to the elevated default risk in `ml.features`.
NORMAL_EXAMPLES = [
    {"user_id": "user-1001", "amount": 42.50, "merchant_category": "groceries", "country": "US"},
    {"user_id": "user-1002", "amount": 89.99, "merchant_category": "retail", "country": "CA"},
    {"user_id": "user-1003", "amount": 15.00, "merchant_category": "food", "country": "GB"},
    {"user_id": "user-1004", "amount": 320.00, "merchant_category": "electronics", "country": "US"},
    {"user_id": "user-1005", "amount": 60.25, "merchant_category": "travel", "country": "AU"},
]
SUSPICIOUS_EXAMPLES = [
    {
        "user_id": "user-2001",
        "amount": 4800.00,
        "merchant_category": "cryptocurrency",
        "country": "NG",
    },
    {
        "user_id": "user-2002",
        "amount": 6500.00,
        "merchant_category": "wire_transfer",
        "country": "RU",
    },
    {
        "user_id": "user-2003",
        "amount": 2200.00,
        "merchant_category": "gambling",
        "country": "KY",
    },
    {
        "user_id": "user-2004",
        "amount": 999.00,
        "merchant_category": "cash_advance",
        "country": "US",
    },
]


def generate_sample_transactions(
    hour_normal: int = 14,
    hour_suspicious: int = 3,
    reference: datetime | None = None,
) -> list[dict]:
    """Return a small, realistic mix of normal and suspicious transactions."""
    reference = (reference or datetime.now(timezone.utc)).replace(
        minute=0, second=0, microsecond=0
    )
    samples = []
    for index, example in enumerate(NORMAL_EXAMPLES):
        timestamp = reference.replace(hour=hour_normal) - timedelta(days=index)
        samples.append({**example, "timestamp": timestamp.isoformat()})
    for index, example in enumerate(SUSPICIOUS_EXAMPLES):
        timestamp = reference.replace(hour=hour_suspicious) - timedelta(hours=index)
        samples.append({**example, "timestamp": timestamp.isoformat()})
    return samples
