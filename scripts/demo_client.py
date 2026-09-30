"""Command-line demo that sends sample transactions to a running FraudPulse API.

Start the API first (`make dev`, or `docker run -p 8000:8000 fraudpulse`),
then run this script to see how FraudPulse scores a realistic mix of normal
and suspicious transactions - a quick way to demo the system to someone else.

Usage:
    python scripts/demo_client.py
    python scripts/demo_client.py --host http://localhost:8000 --api-key secret
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

SAMPLE_TRANSACTIONS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "sample_transactions.json"
)


def load_sample_transactions() -> list[dict]:
    if SAMPLE_TRANSACTIONS_PATH.exists():
        return json.loads(SAMPLE_TRANSACTIONS_PATH.read_text())
    from ml.data import generate_sample_transactions  # local import: optional fallback

    return generate_sample_transactions()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--host", default="http://localhost:8000", help="Base URL of a running FraudPulse API"
    )
    parser.add_argument(
        "--api-key", default=None, help="Value for the X-API-Key header, if required"
    )
    args = parser.parse_args()

    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    transactions = load_sample_transactions()

    print(f"Sending {len(transactions)} sample transactions to {args.host} ...\n")
    header_line = (
        f"{'user_id':<12} {'amount':>10} {'merchant':<16} {'risk':>6} "
        f"{'anomaly':>8}  risk_factors"
    )
    print(header_line)
    print("-" * len(header_line))

    for transaction in transactions:
        response = requests.post(
            f"{args.host}/score", json=transaction, headers=headers, timeout=10
        )
        response.raise_for_status()
        result = response.json()
        factors = ", ".join(result["risk_factors"]) or "-"
        print(
            f"{transaction['user_id']:<12} {transaction['amount']:>10.2f} "
            f"{transaction['merchant_category']:<16} {result['risk_score']:>6.2f} "
            f"{str(result['is_anomaly']):>8}  {factors}"
        )


if __name__ == "__main__":
    main()
