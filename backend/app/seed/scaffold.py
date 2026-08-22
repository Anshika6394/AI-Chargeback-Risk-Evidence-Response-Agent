"""Seed-data scaffolding for deterministic synthetic demo data."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.seed.generate_synthetic import SeedSummary, seed_synthetic

logger = logging.getLogger(__name__)


def seed_synthetic_demo_data(db: Session) -> SeedSummary:
    try:
        counts = seed_synthetic(db)
    except IntegrityError:
        db.rollback()
        logger.warning("Synthetic seed encountered existing rows; rolling back and retrying")
        counts = seed_synthetic(db)
    logger.info("Synthetic seed counts: %s", counts)
    return counts
