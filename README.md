# FraudPulse

**A real-time payment transaction anomaly detection API you can run, test, and demo in minutes.**

[![CI](https://github.com/officialbryx/pulsor/actions/workflows/ci.yml/badge.svg)](https://github.com/officialbryx/pulsor/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

FraudPulse scores incoming payment transactions with a **hybrid ML pipeline**
(unsupervised anomaly detection + a supervised fraud classifier), explains
every score with **SHAP**, and ships with a browser dashboard so anyone —
not just engineers — can try it and see how it behaves.

> **Disclaimer**: The bundled model is trained entirely on synthetic data for
> demonstration and learning purposes. It is a reference architecture for a
> fintech fraud-scoring service, **not** a production fraud detector. See
> [Production hardening](#production-hardening) before using it with real data.

## Contents

- [Why this project](#why-this-project)
- [Features](#features)
- [Quickstart](#quickstart)
- [Try it: 3 ways to test the system](#try-it-3-ways-to-test-the-system)
- [Architecture](#architecture)
- [API reference](#api-reference)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Production hardening](#production-hardening)
- [License](#license)

## Why this project

Fraud/anomaly scoring is one of the most common real-world ML use cases in
fintech, but most public examples are either a bare Jupyter notebook or a
toy "hello world" API. FraudPulse aims to sit in between: a small enough
codebase to read in one sitting, but structured the way a real service would
be — separate ML and API layers, model persistence, explainability, tests,
Docker, and CI — so it's useful both as a **learning reference** and as a
**starting point** for a real project.

## Features

- **Hybrid scoring model** — an Isolation Forest (unsupervised novelty
  detection) and an XGBoost classifier (supervised fraud probability) are
  blended into one `risk_score`, mirroring how real fraud platforms layer
  detection strategies.
- **Explainability** — `POST /explain` returns per-feature SHAP
  contributions, so every score can be justified to an analyst or auditor.
- **Batch scoring** — `POST /score/batch` scores up to 500 transactions in
  one call for backfills or nightly review jobs.
- **Browser test dashboard** — a zero-dependency HTML/JS page (served at `/`)
  for scoring and explaining transactions by hand, with one-click example
  transactions.
- **Demo CLI** — `scripts/demo_client.py` sends a realistic mix of normal and
  suspicious transactions to a running instance and prints a readable
  summary, great for showing the system to someone else.
- **Slack alerting** — optional webhook notification for high-risk
  transactions.
- **Optional API key auth** — disabled by default for frictionless testing,
  one environment variable to lock it down.
- **Train/serve separation** — `ml.train` fits and persists the model with
  `joblib`; the API loads the artifact at startup and falls back to training
  on the fly if it's missing.
- **Docker + Compose + CI** — a non-root, multi-stage production image, a
  one-command `docker compose up`, and a GitHub Actions workflow that lints,
  tests, and builds on every push.

## Quickstart

### Option A — Docker (fastest way to try it)

```bash
docker compose up --build
```

Then open **http://localhost:8000/** in a browser for the test dashboard, or
**http://localhost:8000/docs** for interactive Swagger docs.

### Option B — Local development

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
make install                   # pip install -e ".[dev]"
make dev                       # uvicorn app.main:app --reload
```

The API listens on `http://localhost:8000`. The first run trains and saves a
model to `models/fraud_model.joblib` automatically (takes well under a
second); subsequent runs load it instantly.

To enable Slack alerts, set `SLACK_WEBHOOK_URL` (see [Configuration](#configuration)):

```bash
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..." make dev
```

## Try it: 3 ways to test the system

**1. Browser dashboard** — open `/` and click **Load suspicious example** →
**Score transaction** → **Explain result** to see a full anomalous
transaction walkthrough, including the SHAP breakdown, without writing any
code.

**2. Demo script** — with the API running in another terminal:

```bash
make demo   # python scripts/demo_client.py
```

```text
Sending 9 sample transactions to http://localhost:8000 ...

user_id          amount merchant           risk  anomaly  risk_factors
----------------------------------------------------------------------
user-1001         42.50 groceries          0.17    False  -
user-1002         89.99 retail             0.01    False  -
user-2002       6500.00 wire_transfer      1.00     True  Unusually high transaction amount, High-risk merchant category, ...
```

**3. curl / Swagger** — see [API reference](#api-reference) below, or open
`/docs` for a fully interactive OpenAPI UI.

## Architecture

```mermaid
flowchart LR
    T[Transaction] --> F[Feature transform]
    F --> IF[Isolation Forest<br/>anomaly score]
    F --> XGB[XGBoost<br/>fraud probability]
    IF --> Blend[Weighted blend<br/>+ risk factors]
    XGB --> Blend
    Blend --> Score[risk_score / is_anomaly]
    XGB --> SHAP[SHAP TreeExplainer]
    SHAP --> Explain[/explain]
    Score -. high risk .-> Slack[Slack webhook]
```

`app/` is the FastAPI web layer (routing, schemas, auth, alerting, the test
dashboard). `ml/` is the model layer (features, synthetic data, training,
persistence, scoring, explanations) and has no dependency on `app/`, so it
can be reused outside the web service. Full details, sequence diagrams, and
the reasoning behind the synthetic training data live in
[docs/architecture.md](docs/architecture.md).

## API reference

| Endpoint            | Method | Auth\*    | Purpose                                   |
| -------------------- | ------ | --------- | ------------------------------------------ |
| `/health`            | GET    | none      | Liveness check                              |
| `/model/info`        | GET    | none      | Loaded model metadata                       |
| `/score`             | POST   | API key   | Score one transaction                       |
| `/score/batch`       | POST   | API key   | Score up to 500 transactions                |
| `/explain`           | POST   | API key   | SHAP explanation for one transaction        |
| `/`                  | GET    | none      | Browser test dashboard                      |
| `/docs`, `/redoc`    | GET    | none      | Interactive API documentation               |

\*API key is only enforced when the `API_KEY` environment variable is set.

Full request/response schemas, error codes, and more examples are in
[docs/api.md](docs/api.md).

## Configuration

All configuration is via environment variables (see [.env.example](.env.example));
every value is optional and has a safe default.

| Variable              | Default                       | Purpose                                             |
| ---------------------- | ------------------------------ | ---------------------------------------------------- |
| `SLACK_WEBHOOK_URL`   | *(unset)*                     | Send Slack alerts for high-risk transactions        |
| `API_KEY`             | *(unset)*                     | Require `X-API-Key` on scoring endpoints            |
| `HIGH_RISK_THRESHOLD` | `0.8`                          | Risk score at/above which a transaction is anomalous |
| `CORS_ORIGINS`        | `*`                            | Comma-separated allowed origins                      |
| `MODEL_PATH`          | `models/fraud_model.joblib`   | Where the trained model is stored/loaded             |
| `LOG_LEVEL`           | `INFO`                        | Python logging level                                 |

## Project structure

```text
app/                      FastAPI web layer
  main.py                   App factory, middleware, dashboard route
  config.py                 Environment configuration (API key, Slack, CORS)
  security.py                Optional X-API-Key enforcement
  schemas.py                 Request/response models (pydantic)
  alerts.py                   Slack webhook integration
  logging_config.py           Structured logging setup
  routers/
    health.py                  /health, /model/info
    scoring.py                  /score, /score/batch, /explain
  static/index.html           Browser test dashboard (vanilla HTML/JS)

ml/                        Model layer (no dependency on app/)
  features.py                Shared feature transform (train + serve)
  data.py                     Synthetic data generators
  model.py                    TransactionModel: train/save/load/score/explain
  train.py                     `python -m ml.train` CLI
  config.py                   Model path / risk threshold configuration

scripts/
  demo_client.py             Sends sample transactions to a running API
  generate_sample_transactions.py   Regenerates data/sample_transactions.json

data/sample_transactions.json   Bundled example transactions for demos/tests
models/                    Trained model artifact (gitignored, generated)
docs/architecture.md      Design rationale + diagrams
docs/api.md                Full endpoint reference
tests/                     pytest suite mirroring the app/ml layout
.github/workflows/ci.yml  Lint + test + Docker build on every push
```

## Testing

```bash
make test        # pytest -v
make lint         # ruff check
```

The suite covers feature engineering, model determinism and persistence,
the full HTTP API (including auth and batch scoring), and Slack alerting —
24 tests, no network or external services required.

## Production hardening

This project intentionally keeps scope small. Before pointing it at real
payment data, see the full checklist in
[docs/architecture.md](docs/architecture.md#security--production-considerations),
including: real authentication (OAuth2/mTLS), rate limiting, an audit-log
datastore, model registry/monitoring, and replacing the synthetic training
data in `ml/data.py` with real, versioned historical transactions.

## License

[MIT](LICENSE)

