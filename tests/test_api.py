"""Integration tests for the FraudPulse HTTP API."""
from __future__ import annotations

NORMAL_TRANSACTION = {
    "user_id": "user-123",
    "amount": 129.95,
    "merchant_category": "groceries",
    "timestamp": "2026-09-30T12:30:00Z",
    "country": "US",
}

SUSPICIOUS_TRANSACTION = {
    "user_id": "user-999",
    "amount": 7200.00,
    "merchant_category": "cryptocurrency",
    "timestamp": "2026-09-30T03:15:00Z",
    "country": "KY",
}


def test_health(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_info(client) -> None:
    response = client.get("/model/info")

    assert response.status_code == 200
    body = response.json()
    assert body["version"]
    assert body["feature_names"]
    assert 0 <= body["fraud_rate"] <= 1


def test_index_serves_dashboard(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_score(client) -> None:
    response = client.post("/score", json=NORMAL_TRANSACTION)

    assert response.status_code == 200
    result = response.json()
    assert 0 <= result["risk_score"] <= 1
    assert isinstance(result["is_anomaly"], bool)
    assert isinstance(result["risk_factors"], list)
    assert 0 <= result["components"]["anomaly_score"] <= 1
    assert 0 <= result["components"]["fraud_probability"] <= 1


def test_score_flags_suspicious_transaction(client) -> None:
    response = client.post("/score", json=SUSPICIOUS_TRANSACTION)

    assert response.status_code == 200
    result = response.json()
    assert result["is_anomaly"] is True
    assert result["risk_factors"]


def test_score_rejects_invalid_amount(client) -> None:
    response = client.post("/score", json={**NORMAL_TRANSACTION, "amount": 0})

    assert response.status_code == 422


def test_score_batch(client) -> None:
    response = client.post(
        "/score/batch",
        json={"transactions": [NORMAL_TRANSACTION, SUSPICIOUS_TRANSACTION]},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2


def test_score_batch_rejects_empty_list(client) -> None:
    response = client.post("/score/batch", json={"transactions": []})

    assert response.status_code == 422


def test_explain(client) -> None:
    response = client.post("/explain", json=SUSPICIOUS_TRANSACTION)

    assert response.status_code == 200
    body = response.json()
    assert len(body["contributions"]) == 4
    assert {"feature", "value", "shap_value", "direction"} <= body["contributions"][0].keys()


def test_api_key_enforced_when_configured(client, monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")

    unauthorized = client.post("/score", json=NORMAL_TRANSACTION)
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/score", json=NORMAL_TRANSACTION, headers={"X-API-Key": "test-secret"}
    )
    assert authorized.status_code == 200


def test_api_key_not_required_by_default(client, monkeypatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)

    response = client.post("/score", json=NORMAL_TRANSACTION)

    assert response.status_code == 200

