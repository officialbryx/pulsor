"""Regenerate the bundled sample transactions used by the demo client and UI.

Usage:
    python scripts/generate_sample_transactions.py
"""
from __future__ import annotations

import json
from pathlib import Path

from ml.data import generate_sample_transactions

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_transactions.json"


def main() -> None:
    transactions = generate_sample_transactions()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(transactions, indent=2) + "\n")
    print(f"Wrote {len(transactions)} sample transactions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
