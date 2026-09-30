# API Reference

Interactive documentation is also available at `/docs` (Swagger UI) and
`/redoc` on a running instance. A browser-based test dashboard is served at
`/`.

All request/response bodies are JSON. All endpoints are versioned implicitly
via `model_version` in responses, not via the URL path.

## Authentication

Set the `API_KEY` environment variable to require every scoring request to
include a matching header:

```text
X-API-Key: <your-key>
```

`GET /health` and `GET /model/info` are never protected. When `API_KEY` is
unset (the default), no authentication is required anywhere.

## `GET /health`

Liveness check.

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok"}
```

## `GET /model/info`

Metadata about the currently loaded model.

```bash
curl http://localhost:8000/model/info
```

```json
{
  "version": "1.0.0",
  "trained_at": "2026-09-30T14:53:33.827711+00:00",
  "training_rows": 5000,
  "fraud_rate": 0.06,
  "train_accuracy": 0.9775,
  "feature_names": ["log_amount", "hour", "merchant_risk", "country_risk"]
}
```

## `POST /score`

Score a single transaction.

Request body:

| Field               | Type    | Notes                                  |
| ------------------- | ------- | --------------------------------------- |
| `user_id`           | string  | Free-form identifier                    |
| `amount`            | float   | Must be `> 0`                           |
| `merchant_category` | string  | e.g. `groceries`, `wire_transfer`       |
| `timestamp`         | string  | ISO 8601, e.g. `2026-09-30T12:30:00Z`   |
| `country`           | string  | 2-3 letter country code                 |

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

```json
{
  "risk_score": 0.17,
  "is_anomaly": false,
  "risk_factors": [],
  "model_version": "1.0.0",
  "components": {
    "anomaly_score": 0.37,
    "fraud_probability": 0.00003
  }
}
```

A suspicious transaction:

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-999",
    "amount": 6500.00,
    "merchant_category": "wire_transfer",
    "timestamp": "2026-09-30T03:00:00Z",
    "country": "RU"
  }'
```

```json
{
  "risk_score": 1.0,
  "is_anomaly": true,
  "risk_factors": [
    "Unusually high transaction amount",
    "High-risk merchant category",
    "Unfamiliar transaction country",
    "Transaction at an unusual hour"
  ],
  "model_version": "1.0.0",
  "components": { "anomaly_score": 1.0, "fraud_probability": 0.997 }
}
```

Validation errors return `422 Unprocessable Entity` with pydantic's standard
error format (e.g. `amount <= 0`).

## `POST /score/batch`

Score up to 500 transactions in one call - useful for nightly batch review
or backfilling scores.

```bash
curl -X POST http://localhost:8000/score/batch \
  -H "Content-Type: application/json" \
  -d '{"transactions": [
    {"user_id": "u1", "amount": 20, "merchant_category": "groceries", "timestamp": "2026-09-30T12:00:00Z", "country": "US"},
    {"user_id": "u2", "amount": 7000, "merchant_category": "gambling", "timestamp": "2026-09-30T03:00:00Z", "country": "KY"}
  ]}'
```

Response: `{"results": [ScoreResponse, ScoreResponse]}` in request order.

## `POST /explain`

Explain the supervised model's fraud probability for a single transaction
using SHAP values, ranked by contribution magnitude.

```bash
curl -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-999",
    "amount": 6500.00,
    "merchant_category": "wire_transfer",
    "timestamp": "2026-09-30T03:00:00Z",
    "country": "RU"
  }'
```

```json
{
  "risk_score": 1.0,
  "fraud_probability": 0.997,
  "base_value": -2.871,
  "contributions": [
    {"feature": "log_amount", "value": 8.78, "shap_value": 6.36, "direction": "increases_risk"},
    {"feature": "hour", "value": 3.0, "shap_value": 1.13, "direction": "increases_risk"},
    {"feature": "merchant_risk", "value": 0.8, "shap_value": 0.73, "direction": "increases_risk"},
    {"feature": "country_risk", "value": 0.55, "shap_value": 0.50, "direction": "increases_risk"}
  ]
}
```

`shap_value` is in log-odds space relative to `base_value` (the model's
average output). Positive values push the fraud probability up; negative
values pull it down. `contributions` is sorted by `|shap_value|` descending.

## Error responses

| Status | Meaning                                             |
| ------ | ---------------------------------------------------- |
| `401`  | `API_KEY` is configured and the header is missing/wrong |
| `422`  | Request body failed validation                        |
| `500`  | Unexpected server error                                |
