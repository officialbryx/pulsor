from fastapi.testclient import TestClient

from app import alerts
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score() -> None:
    response = client.post(
        "/score",
        json={
            "user_id": "user-123",
            "amount": 129.95,
            "merchant_category": "groceries",
            "timestamp": "2026-09-30T12:30:00Z",
            "country": "US",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert 0 <= result["risk_score"] <= 1
    assert isinstance(result["is_anomaly"], bool)
    assert isinstance(result["risk_factors"], list)


def test_score_rejects_invalid_amount() -> None:
    response = client.post(
        "/score",
        json={
            "user_id": "user-123",
            "amount": 0,
            "merchant_category": "groceries",
            "timestamp": "2026-09-30T12:30:00Z",
            "country": "US",
        },
    )

    assert response.status_code == 422


def test_high_risk_score_sends_slack_alert(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/webhook")
    sent = {}

    def fake_post(url, *, json, timeout):
        sent.update(url=url, payload=json, timeout=timeout)

        class Response:
            @staticmethod
            def raise_for_status() -> None:
                pass

        return Response()

    monkeypatch.setattr(alerts.requests, "post", fake_post)
    result = {"risk_score": 0.81, "is_anomaly": False, "risk_factors": []}

    assert alerts.send_slack_alert(
        {
            "user_id": "user-123",
            "amount": 200,
            "merchant_category": "groceries",
            "country": "US",
        },
        result,
    )
    assert sent["payload"]["text"].startswith(":warning:")
    assert sent["timeout"] == 5
