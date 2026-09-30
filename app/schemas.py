"""Pydantic request/response models for the FraudPulse API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    user_id: str
    amount: float = Field(gt=0)
    merchant_category: str = Field(min_length=1)
    timestamp: datetime
    country: str = Field(min_length=2, max_length=3)


class ScoreComponents(BaseModel):
    anomaly_score: float = Field(
        ge=0, le=1, description="Unsupervised novelty score (Isolation Forest)"
    )
    fraud_probability: float = Field(
        ge=0, le=1, description="Supervised fraud probability (XGBoost)"
    )


class ScoreResponse(BaseModel):
    risk_score: float = Field(ge=0, le=1)
    is_anomaly: bool
    risk_factors: list[str]
    model_version: str
    components: ScoreComponents


class BatchScoreRequest(BaseModel):
    transactions: list[Transaction] = Field(min_length=1, max_length=500)


class BatchScoreResponse(BaseModel):
    results: list[ScoreResponse]


class FeatureContribution(BaseModel):
    feature: str
    value: float
    shap_value: float
    direction: str


class ExplainResponse(BaseModel):
    risk_score: float = Field(ge=0, le=1)
    fraud_probability: float = Field(ge=0, le=1)
    base_value: float
    contributions: list[FeatureContribution]


class ModelInfoResponse(BaseModel):
    version: str
    trained_at: datetime
    training_rows: int
    fraud_rate: float
    train_accuracy: float
    feature_names: list[str]
