"""Unit tests for feature engineering (`ml.features`)."""
from __future__ import annotations

from datetime import datetime, timezone

from ml.features import FEATURE_NAMES, transform


def test_transform_produces_expected_columns() -> None:
    features = transform(
        {
            "amount": 100.0,
            "merchant_category": "Groceries",
            "country": "us",
            "timestamp": datetime(2026, 9, 30, 3, 15, tzinfo=timezone.utc),
        }
    )

    assert list(features.columns) == FEATURE_NAMES
    assert features.loc[0, "hour"] == 3
    assert features.loc[0, "merchant_risk"] == 0.05
    assert features.loc[0, "country_risk"] == 0.05


def test_transform_is_case_and_whitespace_insensitive() -> None:
    features = transform(
        {
            "amount": 100.0,
            "merchant_category": "  GROCERIES  ",
            "country": " us ",
            "timestamp": datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc),
        }
    )

    assert features.loc[0, "merchant_risk"] == 0.05
    assert features.loc[0, "country_risk"] == 0.05


def test_transform_defaults_unknown_categories_to_elevated_risk() -> None:
    features = transform(
        {
            "amount": 50.0,
            "merchant_category": "unknown-category",
            "country": "ZZ",
            "timestamp": datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc),
        }
    )

    assert features.loc[0, "merchant_risk"] > 0.5
    assert features.loc[0, "country_risk"] > 0.5


def test_transform_localizes_naive_timestamps_to_utc() -> None:
    features = transform(
        {
            "amount": 50.0,
            "merchant_category": "groceries",
            "country": "US",
            "timestamp": datetime(2026, 9, 30, 9, 0),
        }
    )

    assert features.loc[0, "hour"] == 9
