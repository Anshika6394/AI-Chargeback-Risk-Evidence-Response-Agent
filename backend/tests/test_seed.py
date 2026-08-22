"""Tests for deterministic synthetic data seeding."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.customer import Customer
from app.models.dispute import Dispute
from app.models.transaction import Transaction
from app.seed.generate_synthetic import ID_PREFIX


@pytest.fixture()
def seeded_client() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    """Provide a TestClient wired to an isolated in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: Settings(app_env="development", database_url="sqlite:///:memory:")

    try:
        yield TestClient(app), TestingSessionLocal
    finally:
        app.dependency_overrides.clear()


def test_seed_endpoint_responds_200_in_development(seeded_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = seeded_client

    response = client.post("/api/v1/seed")

    assert response.status_code == 200
    assert response.json() == {
        "status": "seeded",
        "counts": {"customers": 125, "transactions": 260, "disputes": 32, "devices": 42},
    }


def test_seed_endpoint_returns_403_in_production(seeded_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = seeded_client
    app.dependency_overrides[get_settings] = lambda: Settings(app_env="production", database_url="sqlite:///:memory:")

    response = client.post("/api/v1/seed")

    assert response.status_code == 403
    assert response.json()["detail"] == "Seeding is only available in development"


def test_database_has_expected_counts_after_seed(seeded_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, TestingSessionLocal = seeded_client

    first_response = client.post("/api/v1/seed")
    second_response = client.post("/api/v1/seed")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    with TestingSessionLocal() as session:
        customer_count = len(session.scalars(select(Customer).where(Customer.email.like("phase2.%@synthetic.example.test"))).all())
        transaction_count = len(
            session.scalars(select(Transaction).where(Transaction.transaction_id.like(f"{ID_PREFIX}%"))).all()
        )
        dispute_count = len(session.scalars(select(Dispute).where(Dispute.evidence_summary.like("Synthetic demo dispute%"))).all())

    assert customer_count == 125
    assert transaction_count == 260
    assert dispute_count == 32
    assert second_response.json()["counts"] == {"customers": 125, "transactions": 260, "disputes": 32, "devices": 42}


def test_seeded_risk_patterns_include_disputed_transactions(
    seeded_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, TestingSessionLocal = seeded_client
    client.post("/api/v1/seed")

    with TestingSessionLocal() as session:
        disputed_transactions = session.scalars(
            select(Transaction).join(Dispute).where(Transaction.transaction_id.like(f"{ID_PREFIX}%"))
        ).all()
        high_amount_disputed = [transaction for transaction in disputed_transactions if transaction.amount >= 8000]

    assert len(disputed_transactions) == 32
    assert len(high_amount_disputed) >= 20
