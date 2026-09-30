"""Transaction scoring endpoints.

All routes here require the `X-API-Key` header when the `API_KEY` environment
variable is configured (see `app.security`).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.alerts import send_slack_alert
from app.schemas import (
    BatchScoreRequest,
    BatchScoreResponse,
    ExplainResponse,
    ScoreResponse,
    Transaction,
)
from app.security import require_api_key
from ml.model import model

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scoring"], dependencies=[Depends(require_api_key)])


def _score_and_alert(transaction: Transaction) -> dict:
    transaction_data = transaction.model_dump()
    result = model.score(transaction_data)
    logger.info(
        "scored transaction user_id=%s risk_score=%.3f is_anomaly=%s",
        transaction_data["user_id"],
        result["risk_score"],
        result["is_anomaly"],
    )
    send_slack_alert(transaction_data, result)
    return result


@router.post("/score", response_model=ScoreResponse)
def score(transaction: Transaction) -> dict:
    return _score_and_alert(transaction)


@router.post("/score/batch", response_model=BatchScoreResponse)
def score_batch(request: BatchScoreRequest) -> dict:
    return {"results": [_score_and_alert(transaction) for transaction in request.transactions]}


@router.post("/explain", response_model=ExplainResponse)
def explain(transaction: Transaction) -> dict:
    return model.explain(transaction.model_dump())
