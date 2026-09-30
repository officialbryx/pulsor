"""Train and persist the FraudPulse hybrid scoring model.

Usage:
    python -m ml.train
    python -m ml.train --seed 7 --output models/fraud_model.joblib
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from ml.config import get_model_path
from ml.model import TransactionModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducible training"
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Where to save the model artifact"
    )
    args = parser.parse_args()

    output = args.output or get_model_path()

    started = time.perf_counter()
    trained_model = TransactionModel.train(seed=args.seed)
    saved_path = trained_model.save(output)
    elapsed = time.perf_counter() - started

    metadata = trained_model.metadata
    print(f"Trained FraudPulse model v{metadata.version} in {elapsed:.2f}s")
    print(f"  training rows        : {metadata.training_rows}")
    print(f"  synthetic fraud rate : {metadata.fraud_rate:.2%}")
    print(f"  train accuracy       : {metadata.train_accuracy:.4f}")
    print(f"  saved to             : {saved_path}")


if __name__ == "__main__":
    main()
