"""Tests for Phase 3 ML training and reusable risk prediction."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.init_db import init_db
from app.ml.features import FEATURE_COLUMNS, build_training_frame
from app.ml.prediction import predict_risk, probability_to_score, risk_level_for_score
from app.ml.training import build_preprocessor, train_and_persist
from app.seed.generate_synthetic import seed_synthetic


def _training_frame():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    init_db(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        seed_synthetic(db)
        return build_training_frame(db)


def test_preprocessor_transforms_mixed_features() -> None:
    frame = _training_frame()
    transformed = build_preprocessor().fit_transform(frame[FEATURE_COLUMNS])

    assert len(FEATURE_COLUMNS) == 22
    assert transformed.shape[0] == len(frame)
    assert transformed.shape[1] > len(FEATURE_COLUMNS)


def test_training_compares_three_models_and_persists_reloadable_artifact(tmp_path: Path) -> None:
    frame = _training_frame()
    result = train_and_persist(frame, tmp_path)

    assert set(result.validation_metrics) == {"logistic_regression", "random_forest", "xgboost"}
    for metrics in result.validation_metrics.values():
        assert {"precision", "recall", "f1", "accuracy", "roc_auc", "confusion_matrix"} <= set(metrics)
    assert result.artifact_path.exists()
    assert result.metadata_path.exists()

    settings = Settings(ml_model_artifact_path=str(result.artifact_path), risk_low_threshold=35, risk_high_threshold=70)
    prediction = predict_risk(frame[FEATURE_COLUMNS].iloc[0].to_dict(), settings=settings)
    assert 0.0 <= prediction.probability <= 1.0
    assert 0 <= prediction.risk_score <= 100
    assert prediction.risk_level in {"LOW", "MEDIUM", "HIGH"}


def test_training_is_reproducible_with_fixed_seed(tmp_path: Path) -> None:
    frame = _training_frame()
    first = train_and_persist(frame, tmp_path / "first")
    second = train_and_persist(frame, tmp_path / "second")

    assert first.selected_model == second.selected_model
    assert first.validation_metrics == second.validation_metrics


def test_risk_score_thresholds() -> None:
    assert probability_to_score(0.704) == 70
    assert risk_level_for_score(34, 35, 70) == "LOW"
    assert risk_level_for_score(35, 35, 70) == "MEDIUM"
    assert risk_level_for_score(70, 35, 70) == "HIGH"
