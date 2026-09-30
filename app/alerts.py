import html
import logging

import requests

from app.config import get_slack_webhook_url
from ml.config import get_high_risk_threshold

logger = logging.getLogger(__name__)


def send_slack_alert(transaction: dict, result: dict) -> bool:
    if not result["is_anomaly"] and result["risk_score"] <= get_high_risk_threshold():
        return False

    webhook_url = get_slack_webhook_url()
    if not webhook_url:
        return False

    user_id = html.escape(str(transaction["user_id"]), quote=False)
    category = html.escape(transaction["merchant_category"], quote=False)
    country = html.escape(transaction["country"], quote=False)
    payload = {
        "text": (
            ":warning: *FraudPulse transaction alert*\n"
            f"User: {user_id} | Amount: {transaction['amount']:.2f} "
            f"| Category: {category} | Country: {country}\n"
            f"Risk score: {result['risk_score']:.2f}"
        ),
        "unfurl_links": False,
        "unfurl_media": False,
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        logger.warning("failed to send Slack alert for user_id=%s", transaction["user_id"])
        return False
    return True
