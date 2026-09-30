"""Unit tests for the Slack alerting integration (`app.alerts`)."""
from __future__ import annotations

from app import alerts


class _FakeResponse:
    @staticmethod
    def raise_for_status() -> None:
        return None


def test_send_slack_alert_skips_low_risk_transactions(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/webhook")
    calls = []
    monkeypatch.setattr(alerts.requests, "post", lambda *a, **k: calls.append((a, k)))

    sent = alerts.send_slack_alert(
        {"user_id": "user-1", "amount": 10, "merchant_category": "groceries", "country": "US"},
        {"risk_score": 0.1, "is_anomaly": False, "risk_factors": []},
    )

    assert sent is False
    assert calls == []


def test_send_slack_alert_skips_when_webhook_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    sent = alerts.send_slack_alert(
        {"user_id": "user-1", "amount": 10, "merchant_category": "groceries", "country": "US"},
        {"risk_score": 0.95, "is_anomaly": True, "risk_factors": ["Unusual transaction pattern"]},
    )

    assert sent is False


def test_high_risk_score_sends_slack_alert(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/webhook")
    sent = {}

    def fake_post(url, *, json, timeout):
        sent.update(url=url, payload=json, timeout=timeout)
        return _FakeResponse()

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


def test_send_slack_alert_handles_request_failure(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/webhook")

    def failing_post(*args, **kwargs):
        raise alerts.requests.RequestException("boom")

    monkeypatch.setattr(alerts.requests, "post", failing_post)

    sent = alerts.send_slack_alert(
        {"user_id": "user-1", "amount": 10000, "merchant_category": "gambling", "country": "US"},
        {"risk_score": 0.95, "is_anomaly": True, "risk_factors": ["High-risk merchant category"]},
    )

    assert sent is False
