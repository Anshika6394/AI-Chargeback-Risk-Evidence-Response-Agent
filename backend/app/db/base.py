"""SQLAlchemy declarative base and model metadata imports."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# Import models so Base.metadata contains all tables for initialization/migrations.
from app.models.customer import Customer  # noqa: E402,F401
from app.models.device import Device  # noqa: E402,F401
from app.models.dispute import Dispute  # noqa: E402,F401
from app.models.merchant import Merchant  # noqa: E402,F401
from app.models.risk_prediction import RiskPrediction  # noqa: E402,F401
from app.models.transaction import Transaction  # noqa: E402,F401
