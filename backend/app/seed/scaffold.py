"""Seed-data scaffolding for later synthetic demo data phases."""

from sqlalchemy.orm import Session


def seed_synthetic_demo_data(db: Session) -> None:
    """Reserved hook for future synthetic demo data.

    Phase 1 intentionally does not insert final demo data. Later phases must ensure
    every generated row is explicitly synthetic and traceable to deterministic seed logic.
    """
    return None
