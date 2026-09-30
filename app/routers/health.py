"""Health and model introspection endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas import ModelInfoResponse
from ml.model import model

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/model/info", response_model=ModelInfoResponse)
def model_info() -> dict:
    return model.metadata.__dict__
