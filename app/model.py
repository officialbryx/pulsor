from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


MERCHANT_RISK = {
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
COUNTRY_RISK = {"US": 0.05, "CA": 0.05, "GB": 0.05, "AU": 0.1}
FEATURES = ["log_amount", "hour", "merchant_risk", "country_risk"]


def _synthetic_transactions(size: int = 1000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "log_amount": np.log1p(rng.lognormal(mean=4, sigma=1, size=size)),
            "hour": np.clip(rng.normal(loc=13, scale=4, size=size), 0, 23),
            "merchant_risk": rng.choice([0.05, 0.1, 0.2, 0.25], size=size),
            "country_risk": rng.choice([0.05, 0.1], size=size),
        }
    )


class TransactionModel:
    def __init__(self) -> None:
        self.pipeline = make_pipeline(
            StandardScaler(),
            IsolationForest(
                n_estimators=100,
                contamination=0.05,
                random_state=42,
            ),
        )
        training_features = _synthetic_transactions()
        self.pipeline.fit(training_features[FEATURES])
        self._normal_scores = np.sort(
            self.pipeline.decision_function(training_features[FEATURES])
        )

    @staticmethod
    def transform(transaction: dict) -> pd.DataFrame:
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
                    "merchant_risk": MERCHANT_RISK.get(category, 0.65),
                    "country_risk": COUNTRY_RISK.get(country, 0.55),
                }
            ],
            columns=FEATURES,
        )

    def score(self, transaction: dict) -> dict:
        features = self.transform(transaction)
        anomaly_score = self.pipeline.decision_function(features)[0]
        normal_percentile = np.searchsorted(
            self._normal_scores, anomaly_score, side="right"
        ) / len(self._normal_scores)
        risk_score = float(np.clip(1 - normal_percentile, 0, 1))
        risk_factors = []

        if transaction["amount"] >= 5000:
            risk_factors.append("Unusually high transaction amount")
        if features.loc[0, "merchant_risk"] >= 0.8:
            risk_factors.append("High-risk merchant category")
        if features.loc[0, "country_risk"] >= 0.5:
            risk_factors.append("Unfamiliar transaction country")
        if features.loc[0, "hour"] < 5:
            risk_factors.append("Transaction at an unusual hour")

        is_anomaly = risk_score >= 0.8
        if is_anomaly and not risk_factors:
            risk_factors.append("Unusual transaction pattern")

        return {
            "risk_score": risk_score,
            "is_anomaly": is_anomaly,
            "risk_factors": risk_factors,
        }


model = TransactionModel()
