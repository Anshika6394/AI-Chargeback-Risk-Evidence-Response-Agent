"""Deterministic synthetic chargeback data generation."""

from __future__ import annotations

import hashlib
import logging
import random
from decimal import Decimal
from typing import TypedDict

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.device import Device
from app.models.dispute import Dispute
from app.models.merchant import Merchant
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

SYNTHETIC_SEED = 202602
CUSTOMER_COUNT = 125
DEVICE_COUNT = 42
TRANSACTION_COUNT = 260
DISPUTE_COUNT = 32
MERCHANT_COUNT = 12
ID_PREFIX = "synthetic_phase2"


class SeedSummary(TypedDict):
    """Counts returned after deterministic synthetic data seeding."""

    customers: int
    transactions: int
    disputes: int
    devices: int


COUNTRIES = ["IN", "US", "GB", "SG", "AE"]
CURRENCIES_BY_COUNTRY = {"IN": "INR", "US": "USD", "GB": "GBP", "SG": "SGD", "AE": "AED"}
NORMAL_STATUSES = ["captured", "authorized", "settled"]
MERCHANT_CATEGORIES = [
    "digital_goods",
    "travel",
    "electronics",
    "food_delivery",
    "marketplace",
    "gaming",
]
DISPUTE_REASONS = ["fraudulent", "product_not_received", "duplicate", "credit_not_processed"]


def _stable_id(entity: str, index: int) -> str:
    """Return a deterministic UUID-shaped identifier for synthetic rows."""
    digest = hashlib.md5(f"{ID_PREFIX}:{entity}:{index}".encode(), usedforsecurity=False).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def _count_like(db: Session, model: type, column_name: str, pattern: str) -> int:
    column = getattr(model, column_name)
    return int(db.scalar(select(func.count()).select_from(model).where(column.like(pattern))) or 0)


def _summary(db: Session) -> SeedSummary:
    return {
        "customers": _count_like(db, Customer, "email", "phase2.%@synthetic.example.test"),
        "transactions": _count_like(db, Transaction, "transaction_id", f"{ID_PREFIX}%"),
        "disputes": _count_like(db, Dispute, "evidence_summary", "Synthetic demo dispute%"),
        "devices": _count_like(db, Device, "fingerprint", f"{ID_PREFIX}%"),
    }


def generate_synthetic(db: Session) -> SeedSummary:
    """Insert deterministic synthetic customers, devices, transactions, and disputes.

    The generated data is synthetic demo data only. It intentionally encodes simple,
    causal fraud patterns: roughly 13% high-risk transactions have higher velocity,
    unusual amounts, failed/captured status mix, shared devices, and merchant/customer
    geography mismatches. Disputes are preferentially linked to those high-risk
    transactions instead of being assigned randomly.
    """
    fake = Faker()
    Faker.seed(SYNTHETIC_SEED)
    rng = random.Random(SYNTHETIC_SEED)

    customers: list[Customer] = []
    for index in range(CUSTOMER_COUNT):
        country = COUNTRIES[index % len(COUNTRIES)]
        first = fake.first_name()
        last = fake.last_name()
        customers.append(
            Customer(
                id=_stable_id("customer", index),
                email=f"phase2.{index:03d}.{first.lower()}.{last.lower()}@synthetic.example.test",
                full_name=f"{first} {last}",
                country=country,
            )
        )

    merchants: list[Merchant] = []
    for index in range(MERCHANT_COUNT):
        merchants.append(
            Merchant(
                id=_stable_id("merchant", index),
                name=f"Synthetic {fake.company()} {index:02d}",
                category=MERCHANT_CATEGORIES[index % len(MERCHANT_CATEGORIES)],
                country=COUNTRIES[(index * 2) % len(COUNTRIES)],
            )
        )

    devices: list[Device] = []
    for index in range(DEVICE_COUNT):
        customer = customers[index % len(customers)]
        devices.append(
            Device(
                id=_stable_id("device", index),
                customer_id=customer.id,
                fingerprint=f"{ID_PREFIX}_device_fp_{index:03d}_{hashlib.sha256(str(index).encode()).hexdigest()[:16]}",
                ip_address=fake.ipv4_public(),
                user_agent=fake.user_agent(),
            )
        )

    high_risk_indexes = set(range(0, 35))  # 13.5% of 260 transactions.
    transactions: list[Transaction] = []
    high_risk_transactions: list[Transaction] = []
    normal_transactions: list[Transaction] = []
    for index in range(TRANSACTION_COUNT):
        is_high_risk = index in high_risk_indexes
        if is_high_risk:
            # Velocity abuse: a small customer cohort repeatedly uses a shared set of devices.
            customer = customers[index % 8]
            device = devices[index % 5]
            merchant = merchants[(index + 5) % len(merchants)]
            amount = Decimal(str(rng.choice([8999, 12499, 17999, 24999]) + rng.randint(0, 999)))
            status = rng.choice(["captured", "failed", "captured", "settled"])
        else:
            customer = customers[index % len(customers)]
            device = devices[index % len(devices)]
            merchant = merchants[index % len(merchants)]
            amount = Decimal(str(rng.randint(250, 6500))) + (Decimal(rng.randint(0, 99)) / Decimal("100"))
            status = rng.choice(NORMAL_STATUSES)

        transaction = Transaction(
            id=_stable_id("transaction", index),
            transaction_id=f"{ID_PREFIX}_txn_{index:04d}",
            customer_id=customer.id,
            merchant_id=merchant.id,
            device_id=device.id,
            amount=amount.quantize(Decimal("0.01")),
            currency=CURRENCIES_BY_COUNTRY[customer.country or "IN"],
            status=status,
        )
        transactions.append(transaction)
        if is_high_risk:
            high_risk_transactions.append(transaction)
        else:
            normal_transactions.append(transaction)

    disputed_transactions = high_risk_transactions[:24] + normal_transactions[:8]
    disputes: list[Dispute] = []
    for index, transaction in enumerate(disputed_transactions):
        reason = "fraudulent" if index < 24 else DISPUTE_REASONS[(index - 24) % len(DISPUTE_REASONS)]
        disputes.append(
            Dispute(
                id=_stable_id("dispute", index),
                transaction_id=transaction.id,
                customer_id=transaction.customer_id,
                reason_code=reason,
                status=rng.choice(["open", "under_review", "won", "lost"]),
                evidence_summary=(
                    "Synthetic demo dispute linked to deterministic fraud-pattern signals; "
                    "not real customer, transaction, or evidence data."
                ),
            )
        )

    for row in [*customers, *merchants, *devices, *transactions, *disputes]:
        db.merge(row)
    db.commit()

    counts = _summary(db)
    logger.info("Seeded deterministic synthetic demo data: %s", counts)
    return counts
