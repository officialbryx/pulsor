"""Hybrid anomaly-detection + fraud-classification scoring model.

Two complementary models score every transaction, mirroring how real fraud
platforms layer detection strategies:

* An unsupervised Isolation Forest flags transactions that look statistically
  unusual, even if they don't match any previously seen fraud pattern
  (novelty detection - catches the "unknown unknowns").
* A supervised XGBoost classifier estimates the probability that a
  transaction resembles historical fraud, trained on synthetic labeled data
  (`ml.data.generate_labeled_dataset`) - catches known patterns quickly.

The two signals are blended into a single `risk_score`, and the XGBoost
classifier is additionally explained per-transaction with SHAP so callers can
see which features pushed the score up or down (useful for analyst review and
regulatory explainability requirements).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from ml.config import get_high_risk_threshold, get_model_path
from ml.data import generate_feature_frame, generate_labeled_dataset
from ml.features import FEATURE_NAMES, transform

logger = logging.getLogger(__name__)

MODEL_VERSION = "1.0.0"

# Blend weights for the final risk_score. The supervised model is weighted
# slightly higher because it targets known fraud patterns directly; the
# anomaly detector acts as a safety net for novel patterns.
ANOMALY_WEIGHT = 0.45
FRAUD_PROBABILITY_WEIGHT = 0.55


@dataclass
class ModelMetadata:
    version: str
    trained_at: str
    training_rows: int
    fraud_rate: float
    train_accuracy: float
    feature_names: list[str] = field(default_factory=lambda: list(FEATURE_NAMES))


class TransactionModel:
    """Loads, trains, scores, and explains transactions."""

    def __init__(
        self,
        pipeline: Pipeline,
        classifier: XGBClassifier,
        normal_scores: np.ndarray,
        metadata: ModelMetadata,
    ) -> None:
        self.pipeline = pipeline
        self.classifier = classifier
        self.normal_scores = normal_scores
        self.metadata = metadata
        self._explainer: shap.TreeExplainer | None = None

    @classmethod
    def train(cls, seed: int = 42) -> TransactionModel:
        """Fit both models on freshly generated synthetic data."""
        unsupervised_frame = generate_feature_frame(size=1000, seed=seed)
        pipeline = make_pipeline(
            StandardScaler(),
            IsolationForest(n_estimators=100, contamination=0.05, random_state=seed),
        )
        pipeline.fit(unsupervised_frame[FEATURE_NAMES])
        normal_scores = np.sort(pipeline.decision_function(unsupervised_frame[FEATURE_NAMES]))

        features, labels = generate_labeled_dataset(size=4000, fraud_rate=0.06, seed=seed)
        classifier = XGBClassifier(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=seed,
        )
        classifier.fit(features, labels)

        metadata = ModelMetadata(
            version=MODEL_VERSION,
            trained_at=datetime.now(timezone.utc).isoformat(),
            training_rows=len(unsupervised_frame) + len(features),
            fraud_rate=float(labels.mean()),
            train_accuracy=float(classifier.score(features, labels)),
        )
        logger.info(
            "trained model version=%s rows=%d fraud_rate=%.3f accuracy=%.4f",
            metadata.version,
            metadata.training_rows,
            metadata.fraud_rate,
            metadata.train_accuracy,
        )
        return cls(
            pipeline=pipeline,
            classifier=classifier,
            normal_scores=normal_scores,
            metadata=metadata,
        )

    def save(self, path: Path | None = None) -> Path:
        path = path or get_model_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: Path | None = None) -> TransactionModel:
        path = path or get_model_path()
        instance = joblib.load(path)
        if not isinstance(instance, cls):
            raise TypeError(f"{path} does not contain a {cls.__name__}")
        instance._explainer = None
        return instance

    def _anomaly_risk(self, features: pd.DataFrame) -> float:
        anomaly_score = self.pipeline.decision_function(features)[0]
        normal_percentile = np.searchsorted(
            self.normal_scores, anomaly_score, side="right"
        ) / len(self.normal_scores)
        return float(np.clip(1 - normal_percentile, 0, 1))

    def _fraud_probability(self, features: pd.DataFrame) -> float:
        return float(self.classifier.predict_proba(features)[0, 1])

    def _score_from_features(self, transaction: dict, features: pd.DataFrame) -> dict:
        anomaly_risk = self._anomaly_risk(features)
        fraud_probability = self._fraud_probability(features)
        risk_score = float(
            np.clip(
                ANOMALY_WEIGHT * anomaly_risk + FRAUD_PROBABILITY_WEIGHT * fraud_probability,
                0,
                1,
            )
        )

        risk_factors = []
        if transaction["amount"] >= 5000:
            risk_factors.append("Unusually high transaction amount")
        if features.loc[0, "merchant_risk"] >= 0.8:
            risk_factors.append("High-risk merchant category")
        if features.loc[0, "country_risk"] >= 0.5:
            risk_factors.append("Unfamiliar transaction country")
        if features.loc[0, "hour"] < 5:
            risk_factors.append("Transaction at an unusual hour")
        if fraud_probability >= 0.7 and not risk_factors:
            risk_factors.append("Learned pattern resembles historical fraud cases")

        is_anomaly = risk_score >= get_high_risk_threshold()
        if is_anomaly and not risk_factors:
            risk_factors.append("Unusual transaction pattern")

        return {
            "risk_score": risk_score,
            "is_anomaly": is_anomaly,
            "risk_factors": risk_factors,
            "model_version": self.metadata.version,
            "components": {
                "anomaly_score": anomaly_risk,
                "fraud_probability": fraud_probability,
            },
        }

    def score(self, transaction: dict) -> dict:
        features = transform(transaction)
        return self._score_from_features(transaction, features)

    def explain(self, transaction: dict) -> dict:
        """Explain the supervised model's fraud probability with SHAP values."""
        features = transform(transaction)
        score_result = self._score_from_features(transaction, features)

        if self._explainer is None:
            self._explainer = shap.TreeExplainer(self.classifier)
        explanation = self._explainer(features)
        shap_values = np.ravel(explanation.values[0])
        base_value = float(np.ravel(explanation.base_values)[0])

        contributions = sorted(
            (
                {
                    "feature": name,
                    "value": float(features.loc[0, name]),
                    "shap_value": float(shap_value),
                    "direction": "increases_risk" if shap_value > 0 else "decreases_risk",
                }
                for name, shap_value in zip(FEATURE_NAMES, shap_values)
            ),
            key=lambda item: abs(item["shap_value"]),
            reverse=True,
        )

        return {
            "risk_score": score_result["risk_score"],
            "fraud_probability": score_result["components"]["fraud_probability"],
            "base_value": base_value,
            "contributions": contributions,
        }


def load_or_train(path: Path | None = None) -> TransactionModel:
    """Load a persisted model artifact, or train and persist a new one."""
    path = path or get_model_path()
    if path.exists():
        try:
            return TransactionModel.load(path)
        except Exception:
            logger.warning("could not load model from %s, retraining", path, exc_info=True)
    trained = TransactionModel.train()
    trained.save(path)
    return trained


model = load_or_train()
