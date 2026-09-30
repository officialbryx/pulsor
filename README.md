# FraudPulse

FraudPulse is a starter real-time payment transaction anomaly detection API. It
accepts transaction details, returns a mock anomaly risk score, and can send a
Slack alert for high-risk transactions. The included model is a synthetic
baseline for development, not a production fraud detector.

## Architecture

```text
Payment client
     |
     v
FastAPI (/score) ---> Feature transformations ---> Isolation Forest
     |                                              |
     |<---------- score and risk factors <----------+
     |
     +---- high-risk result ----> Slack webhook (optional)
```

## Run locally with Docker

Build and start the service:

```bash
docker build -t fraudpulse .
docker run --rm -p 8000:8000 fraudpulse
```

To enable Slack alerts, pass a webhook URL as an environment variable:

```bash
docker run --rm -p 8000:8000 \
  -e SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..." fraudpulse
```

The service listens on port `8000`. For local development without Docker,
install the project and start Uvicorn:

```bash
python -m pip install .
uvicorn app.main:app --reload
```

The Docker runtime installs only the API and scikit-learn serving dependencies;
XGBoost, SHAP, and pytest are available through the full local project install.

## API

### `GET /health`

Returns the service status:

```json
{"status": "ok"}
```

### `POST /score`

Send an ISO 8601 timestamp and transaction fields:

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "amount": 129.95,
    "merchant_category": "groceries",
    "timestamp": "2026-09-30T12:30:00Z",
    "country": "US"
  }'
```

The response contains a `risk_score` between `0` and `1`, an `is_anomaly`
boolean, and a list of `risk_factors`:

```json
{
  "risk_score": 0.23,
  "is_anomaly": false,
  "risk_factors": []
}
```

Interactive API documentation is available at `/docs`.

## Tests

Run the API tests with:

```bash
python -m pip install .
pytest
```
