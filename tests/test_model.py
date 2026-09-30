"""Unit tests for the hybrid anomaly + fraud classification model (`ml.model`)."""
from __future__ import annotations

from datetime import datetime, timezone

from ml.model import TransactionModel

NORMAL_TRANSACTION = {
    "user_id": "user-1",
    "amount": 42.50,
    "merchant_category": "groceries",
    "timestamp": datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc),
    "country": "US",
}

SUSPICIOUS_TRANSACTION = {
    "user_id": "user-2",
    "amount": 6500.00,
    "merchant_category": "wire_transfer",
    "timestamp": datetime(2026, 9, 30, 3, 0, tzinfo=timezone.utc),
    "country": "RU",
}


def test_train_is_deterministic_for_a_given_seed() -> None:
    first = TransactionModel.train(seed=7)
    second = TransactionModel.train(seed=7)

    assert first.score(NORMAL_TRANSACTION) == second.score(NORMAL_TRANSACTION)


def test_score_contract() -> None:
    model = TransactionModel.train(seed=7)
    result = model.score(NORMAL_TRANSACTION)

    assert 0 <= result["risk_score"] <= 1
    assert 0 <= result["components"]["anomaly_score"] <= 1
    assert 0 <= result["components"]["fraud_probability"] <= 1
    assert result["model_version"] == model.metadata.version


def test_score_flags_suspicious_transaction_higher_than_normal() -> None:
    model = TransactionModel.train(seed=7)

    normal = model.score(NORMAL_TRANSACTION)
    suspicious = model.score(SUSPICIOUS_TRANSACTION)

    assert suspicious["risk_score"] > normal["risk_score"]
    assert suspicious["is_anomaly"] is True
    assert suspicious["risk_factors"]


def test_explain_returns_one_ranked_contribution_per_feature() -> None:
    model = TransactionModel.train(seed=7)
    explanation = model.explain(SUSPICIOUS_TRANSACTION)

    assert len(explanation["contributions"]) == len(model.metadata.feature_names)
    magnitudes = [abs(item["shap_value"]) for item in explanation["contributions"]]
    assert magnitudes == sorted(magnitudes, reverse=True)
    assert {"feature", "value", "shap_value", "direction"} <= explanation["contributions"][0].keys()


def test_save_and_load_roundtrip(tmp_path) -> None:
    model = TransactionModel.train(seed=7)
    path = model.save(tmp_path / "model.joblib")

    loaded = TransactionModel.load(path)

    assert loaded.score(NORMAL_TRANSACTION) == model.score(NORMAL_TRANSACTION)
    assert loaded.metadata == model.metadata
