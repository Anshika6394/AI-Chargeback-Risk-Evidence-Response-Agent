"""Seed-data scaffold for deterministic synthetic demo data."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.seed.generate_synthetic import SeedSummary, generate_synthetic

logger = logging.getLogger(__name__)


def seed_synthetic_demo_data(db: Session) -> SeedSummary:
    """Seed deterministic synthetic demo data and return inserted table counts.

    The underlying generator uses stable identifiers and SQLAlchemy ``merge`` calls,
    making repeated local seeding safe. If an unexpected uniqueness conflict occurs,
    the transaction is rolled back and generation is retried once to preserve the
    endpoint's idempotent behavior for already-seeded databases.
    """
    try:
        counts = generate_synthetic(db)
    except IntegrityError:
        logger.info("Synthetic seed encountered existing rows; rolling back and retrying")
        db.rollback()
        counts = generate_synthetic(db)

    logger.info("Synthetic seed counts: %s", counts)
    return counts
