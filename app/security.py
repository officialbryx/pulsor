"""Optional API key enforcement for scoring endpoints.

Set the `API_KEY` environment variable to require callers to send a matching
`X-API-Key` header. When `API_KEY` is unset (the default), every request is
allowed so the demo API and test dashboard work without any setup - this is a
development default, not a production one (see README "Production Hardening").
"""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import get_api_key


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    configured_key = get_api_key()
    if configured_key and x_api_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
