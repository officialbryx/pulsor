"""FraudPulse FastAPI application: route wiring, middleware, and the demo UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import get_cors_origins
from app.logging_config import configure_logging
from app.routers import health, scoring

configure_logging()

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="FraudPulse",
    description="Real-time payment transaction anomaly detection API",
    version="1.0.0",
)

# Permissive by default so the bundled test dashboard and quick experiments
# work out of the box. Restrict CORS_ORIGINS before deploying with real data.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(scoring.router)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the bundled browser dashboard for manually testing the API."""
    return FileResponse(STATIC_DIR / "index.html")
