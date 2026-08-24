"""Tests for deterministic synthetic data seeding."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.main import app


def make_client(tmp_path: Path, env: str = "development") -> tuple[TestClient, any]:
    db_path = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(db_path, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    init_db(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: Settings(app_env=env, database_url=db_path)
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_seed_endpoint_200_in_development(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post("/api/v1/seed")
    assert response.status_code == 200
    assert response.json()["status"] == "seeded"


def test_seed_endpoint_403_in_production(tmp_path: Path) -> None:
    client = make_client(tmp_path, env="production")
    response = client.post("/api/v1/seed")
    assert response.status_code == 403


def test_database_has_expected_counts_after_seed(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post("/api/v1/seed")
    assert response.status_code == 200
    counts = response.json()["counts"]
    assert counts["customers"] >= 10
    assert counts["transactions"] >= 100
    assert counts["disputes"] >= 10
    assert counts["devices"] >= 10


def test_seed_risk_patterns_include_disputed_transactions(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post("/api/v1/seed")
    assert response.status_code == 200
    counts = response.json()["counts"]
    assert counts["disputes"] >= 10


def test_seed_includes_curated_phase13_demo_transactions(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post("/api/v1/seed")
    assert response.status_code == 200

    for transaction_id in [
        "TX-DEMO-LOW-001",
        "TX-DEMO-MED-001",
        "TX-DEMO-HIGH-001",
        "TX-DEMO-REPEAT-001",
        "TX-DEMO-001",
    ]:
        detail = client.get(f"/api/v1/transactions/{transaction_id}")
        assert detail.status_code == 200
        assert detail.json()["transaction_id"] == transaction_id


def test_hero_demo_transaction_has_repeat_dispute_context(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post("/api/v1/seed")
    assert response.status_code == 200

    hero = client.get("/api/v1/transactions/TX-DEMO-001")
    assert hero.status_code == 200
    body = hero.json()
    assert body["amount"] == "1240.00"
    assert body["status"] == "failed"
    assert body["disputes_count"] == 1
