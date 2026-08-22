"""Feature extraction for synthetic chargeback-risk model training."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session, joinedload

from app.models.dispute import Dispute
from app.models.transaction import Transaction

FEATURE_COLUMNS = [
    "amount",
    "currency",
    "status",
    "customer_country",
    "merchant_category",
    "merchant_country",
    "has_device",
]
TARGET_COLUMN = "has_chargeback"
DATASET_VERSION = "synthetic_phase2_v1"


def transaction_to_feature_row(transaction: Transaction) -> dict[str, Any]:
    """Convert a transaction ORM object into model-ready feature values."""
    return {
        "amount": float(transaction.amount or Decimal("0")),
        "currency": transaction.currency,
        "status": transaction.status,
        "customer_country": transaction.customer.country if transaction.customer else None,
        "merchant_category": transaction.merchant.category if transaction.merchant else None,
        "merchant_country": transaction.merchant.country if transaction.merchant else None,
        "has_device": int(transaction.device_id is not None),
    }


def build_training_frame(db: Session) -> pd.DataFrame:
    """Build a synthetic training frame from database rows and real dispute labels."""
    disputed_transaction_ids = {row[0] for row in db.query(Dispute.transaction_id).all()}
    transactions = (
        db.query(Transaction)
        .options(joinedload(Transaction.customer), joinedload(Transaction.merchant))
        .order_by(Transaction.transaction_id)
        .all()
    )
    rows = []
    for transaction in transactions:
        row = transaction_to_feature_row(transaction)
        row[TARGET_COLUMN] = int(transaction.id in disputed_transaction_ids)
        rows.append(row)
    if not rows:
        raise ValueError("No transactions available for ML training")
    return pd.DataFrame(rows, columns=[*FEATURE_COLUMNS, TARGET_COLUMN])
