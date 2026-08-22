"""Risk prediction, summary, and persisted model metadata endpoints."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.ml.features import FEATURE_COLUMNS
from app.ml.prediction import predict_risk
from app.models.risk_prediction import RiskPrediction
from app.models.transaction import Transaction
from app.schemas.api import ModelInfoResponse, ModelMetricsResponse, RiskPredictRequest, RiskPredictResponse, RiskSummaryResponse

router = APIRouter(prefix="/risk", tags=["risk"])
model_router = APIRouter(prefix="/model", tags=["model"])


def _artifact_payload(settings: Settings, suffix: str) -> dict[str, Any]:
    path = Path(settings.ml_model_artifact_path).with_suffix(suffix)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model metadata artifact is unavailable; train the model first") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model metadata artifact is invalid") from exc


@router.post("/predict", response_model=RiskPredictResponse, status_code=status.HTTP_201_CREATED, summary="Predict risk and store an audit record")
def predict(
    payload: RiskPredictRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RiskPredictResponse:
    """Run the persisted ML model only; the result is a human-review risk assessment, not a financial action."""
    transaction = db.scalar(select(Transaction).where(Transaction.transaction_id == payload.transaction_id))
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    try:
        result = predict_risk(payload.model_dump(exclude={"transaction_id"}), settings=settings)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Risk model artifact is unavailable; train the model first") from exc
    record = RiskPrediction(transaction_id=transaction.id, model_version=result.model_version, risk_score=Decimal(str(result.risk_score / 100)), risk_band=result.risk_level, explanation=None)
    db.add(record)
    db.commit()
    db.refresh(record)
    return RiskPredictResponse(prediction_id=record.id, transaction_id=transaction.transaction_id, probability=result.probability, risk_score=result.risk_score, risk_level=result.risk_level, model_version=result.model_version, model_derived_risk_factors=[factor.__dict__ for factor in result.model_derived_risk_factors])


@router.get("/summary", response_model=RiskSummaryResponse, summary="Get database-derived risk summary")
def risk_summary(db: Annotated[Session, Depends(get_db)]) -> RiskSummaryResponse:
    """Return aggregate counts calculated from stored transactions and prediction audit records."""
    total_transactions = db.scalar(select(func.count()).select_from(Transaction)) or 0
    total_predictions = db.scalar(select(func.count()).select_from(RiskPrediction)) or 0
    average = db.scalar(select(func.avg(RiskPrediction.risk_score)))
    grouped = db.execute(select(RiskPrediction.risk_band, func.count()).group_by(RiskPrediction.risk_band)).all()
    return RiskSummaryResponse(total_transactions=total_transactions, total_predictions=total_predictions, risk_level_counts={band: count for band, count in grouped}, average_risk_score=float(average * 100) if average is not None else None)


@model_router.get("/metrics", response_model=ModelMetricsResponse, summary="Get actual held-out evaluation metrics")
def model_metrics(settings: Annotated[Settings, Depends(get_settings)]) -> ModelMetricsResponse:
    """Expose the persisted Phase 4 evaluation JSON, never hard-coded performance values."""
    payload = _artifact_payload(settings, ".evaluation.json")
    return ModelMetricsResponse(model_version=payload["model_version"], model_type=payload["model_type"], dataset_version=payload["dataset_version"], evaluated_at=payload["evaluated_at"], metrics=payload["metrics"])


@model_router.get("/info", response_model=ModelInfoResponse, summary="Get persisted model metadata")
def model_info(settings: Annotated[Settings, Depends(get_settings)]) -> ModelInfoResponse:
    """Expose safe model registry metadata without returning model internals or artifact contents."""
    payload = _artifact_payload(settings, ".metadata.json")
    return ModelInfoResponse(model_version=payload["model_version"], model_type=payload["model_type"], dataset_version=payload["dataset_version"], feature_count=len(payload.get("feature_list", FEATURE_COLUMNS)), selection_criterion=payload["selection_criterion"], held_out_test_policy=payload["held_out_test_policy"])
