"""Deterministic synthetic chargeback data generation."""

from __future__ import annotations

import hashlib
import logging
import random
from decimal import Decimal
from typing import TypedDict

from faker import Faker
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.device import Device
from app.models.dispute import Dispute
from app.models.merchant import Merchant
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

SYNTHETIC_SEED = 20260822
CUSTOMER_COUNT = 100
DEVICE_COUNT = 42
TRANSACTION_COUNT = 260
MERCHANT_COUNT = 18
DB_PREFIX = "synthetic_phase2"

COUNTRIES = ["IN", "US", "GB", "SG", "AE"]
CURRENCIES_BY_COUNTRY = {"IN": "INR", "US": "USD", "GB": "GBP", "SG": "SGD", "AE": "AED"}
NORMAL_STATUSES = ["captured", "authorized", "settled"]
MERCHANT_CATEGORIES = ["digital_goods", "travel", "food_delivery", "electronics", "gaming"]
DISPUTE_REASONS = ["fraudulent", "product_not_received", "duplicate", "credit_not_processed"]


class SeedSummary(TypedDict):
    customers: int
    transactions: int
    disputes: int
    devices: int


def _stable_id(entity: str, index: int) -> str:
    digest = hashlib.sha256(f"{DB_PREFIX}.{entity}.{index}".encode()).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def seed_synthetic(db: Session) -> SeedSummary:
    fake = Faker()
    Faker.seed(SYNTHETIC_SEED)
    rng = random.Random(SYNTHETIC_SEED)

    customers: list[Customer] = []
    for index in range(CUSTOMER_COUNT):
        country = COUNTRIES[index % len(COUNTRIES)]
        first = fake.first_name()
        last = fake.last_name()
        customers.append(Customer(
            id=_stable_id("customer", index),
            email=f"{DB_PREFIX}.{first.lower()}.{last.lower()}.{index}@synthetic.example.test",
            full_name=f"{first} {last}",
            country=country,
        ))
    db.add_all(customers)

    merchants: list[Merchant] = []
    for index in range(MERCHANT_COUNT):
        merchants.append(Merchant(
            id=_stable_id("merchant", index),
            name=f"{DB_PREFIX}_merchant_{index}",
            category=MERCHANT_CATEGORIES[index % len(MERCHANT_CATEGORIES)],
            country=COUNTRIES[index % len(COUNTRIES)],
        ))
    db.add_all(merchants)

    devices: list[Device] = []
    for index in range(DEVICE_COUNT):
        customer = customers[index % len(customers)]
        devices.append(Device(
            id=_stable_id("device", index),
            customer_id=customer.id,
            fingerprint=f"{DB_PREFIX}_fp_{index}_{rng.randint(1000,9999)}",
            ip_address=fake.ipv4(),
            user_agent=fake.user_agent(),
        ))
    db.add_all(devices)

    high_risk_count = int(TRANSACTION_COUNT * 0.135)
    transactions: list[Transaction] = []
    high_risk_transactions: list[Transaction] = []

    for index in range(TRANSACTION_COUNT):
        is_high_risk = index < high_risk_count
        customer = customers[index % len(customers)]
        merchant = merchants[index % len(merchants)]
        device = devices[index % len(devices)]
        amount = Decimal(rng.randint(2500 if is_high_risk else 100, 50000 if is_high_risk else 10000)) / Decimal("100")
        t = Transaction(
            id=_stable_id("transaction", index),
            transaction_id=f"{DB_PREFIX}_txn_{index:04d}",
            customer_id=customer.id,
            merchant_id=merchant.id,
            device_id=device.id,
            amount=amount,
            currency=CURRENCIES_BY_COUNTRY.get(customer.country or "IN", "INR"),
            status=rng.choice(["captured", "failed"] if is_high_risk else NORMAL_STATUSES),
        )
        transactions.append(t)
        if is_high_risk:
            high_risk_transactions.append(t)
    db.add_all(transactions)

    disputes: list[Dispute] = []
    for index, txn in enumerate(high_risk_transactions):
        disputes.append(Dispute(
            id=_stable_id("dispute", index),
            transaction_id=txn.id,
            customer_id=txn.customer_id,
            reason_code=f"{DB_PREFIX}_{DISPUTE_REASONS[index % len(DISPUTE_REASONS)]}",
            status=rng.choice(["open", "under_review", "won", "lost"]),
            evidence_summary="Synthetic dispute. Not real customer, transaction, or evidence data.",
        ))
    db.add_all(disputes)
    db.commit()

    counts: SeedSummary = {
        "customers": len(customers),
        "transactions": len(transactions),
        "disputes": len(disputes),
        "devices": len(devices),
    }
    logger.info("Seeded synthetic demo data: %s", counts)
    return counts
