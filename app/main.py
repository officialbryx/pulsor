from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.alerts import send_slack_alert
from app.model import model

app = FastAPI(title="FraudPulse", description="Transaction anomaly scoring API")


class Transaction(BaseModel):
    user_id: str
    amount: float = Field(gt=0)
    merchant_category: str = Field(min_length=1)
    timestamp: datetime
    country: str = Field(min_length=2, max_length=3)


class ScoreResponse(BaseModel):
    risk_score: float = Field(ge=0, le=1)
    is_anomaly: bool
    risk_factors: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score(transaction: Transaction) -> dict:
    transaction_data = transaction.model_dump()
    result = model.score(transaction_data)
    send_slack_alert(transaction_data, result)
    return result
