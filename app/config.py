"""Centralized environment configuration for the FraudPulse API.

Every setting is optional and has a safe default so the API and the bundled
test dashboard work immediately without any configuration.
"""
from __future__ import annotations

import os


def get_slack_webhook_url() -> str | None:
    """Slack incoming webhook URL used to alert on high-risk transactions."""
    return os.getenv("SLACK_WEBHOOK_URL") or None


def get_api_key() -> str | None:
    """Shared secret required in the `X-API-Key` header, when set."""
    return os.getenv("API_KEY") or None


def get_cors_origins() -> list[str]:
    """Allowed CORS origins (comma-separated). Defaults to `*` for local testing."""
    raw = os.getenv("CORS_ORIGINS", "*")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
