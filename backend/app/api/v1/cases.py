"""Human-review risk investigation case endpoints; no LLM or financial actions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.risk_case import RiskCase, RiskCaseHistory
from app.models.risk_prediction import RiskPrediction
from app.models.transaction import Transaction
from app.schemas.api import EvidenceItemResponse, RiskCaseCreateRequest, RiskCaseResponse, RiskCaseUpdateRequest, SafeId
from app.services.evidence_builder import build_evidence

router = APIRouter(prefix="/cases", tags=["risk cases"])

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"INVESTIGATING"},
    "INVESTIGATING": {"READY_FOR_REVIEW"},
    "READY_FOR_REVIEW": {"APPROVED", "REJECTED"},
    "APPROVED": {"CLOSED"},
    "REJECTED": {"CLOSED"},
    "CLOSED": set(),
}


def _case_or_404(db: Session, case_id: str) -> RiskCase:
    case = db.scalar(select(RiskCase).options(selectinload(RiskCase.history_entries)).where(RiskCase.case_id == case_id))
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk case not found")
    return case


def _response(case: RiskCase) -> RiskCaseResponse:
    return RiskCaseResponse(
        case_id=case.case_id, transaction_id=case.transaction.transaction_id, prediction_id=case.prediction_id,
        risk_score=case.risk_score, risk_level=case.risk_level, prediction=case.prediction, status=case.status,
        assigned_reviewer=case.assigned_reviewer, created_at=case.created_at, updated_at=case.updated_at,
        history=sorted(case.history_entries, key=lambda entry: entry.created_at),
    )


@router.post("", response_model=RiskCaseResponse, status_code=status.HTTP_201_CREATED, summary="Create an investigation case from an audited ML prediction")
def create_case(payload: RiskCaseCreateRequest, db: Annotated[Session, Depends(get_db)]) -> RiskCaseResponse:
    transaction = db.scalar(select(Transaction).where(Transaction.transaction_id == payload.transaction_id))
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    prediction = db.scalar(select(RiskPrediction).where(RiskPrediction.transaction_id == transaction.id).order_by(RiskPrediction.created_at.desc()))
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An audited risk prediction is required before creating a risk case")
    case = RiskCase(transaction_id=transaction.id, prediction_id=prediction.id, risk_score=prediction.risk_score, risk_level=prediction.risk_band, prediction="CHARGEBACK_RISK", assigned_reviewer=payload.assigned_reviewer)
    db.add(case)
    db.flush()
    db.add(RiskCaseHistory(risk_case_id=case.id, event_type="CASE_CREATED", to_status=case.status, assigned_reviewer=case.assigned_reviewer))
    build_evidence(case, db)
    db.commit()
    return _response(_case_or_404(db, case.case_id))


@router.get("/{case_id}", response_model=RiskCaseResponse, summary="Get a risk investigation case and audit history")
def get_case(case_id: SafeId, db: Annotated[Session, Depends(get_db)]) -> RiskCaseResponse:
    return _response(_case_or_404(db, case_id))


@router.patch("/{case_id}", response_model=RiskCaseResponse, summary="Update reviewer or make a validated case-status transition")
def update_case(case_id: SafeId, payload: RiskCaseUpdateRequest, db: Annotated[Session, Depends(get_db)]) -> RiskCaseResponse:
    case = _case_or_404(db, case_id)
    status_changed = payload.status is not None and payload.status != case.status
    reviewer_changed = "assigned_reviewer" in payload.model_fields_set and payload.assigned_reviewer != case.assigned_reviewer
    if not status_changed and not reviewer_changed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide a changed status or assigned_reviewer")
    if status_changed and payload.status not in ALLOWED_STATUS_TRANSITIONS[case.status]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Invalid case status transition: {case.status} to {payload.status}")
    previous_status = case.status
    if status_changed:
        case.status = payload.status
    if reviewer_changed:
        case.assigned_reviewer = payload.assigned_reviewer
    db.add(RiskCaseHistory(risk_case_id=case.id, event_type="STATUS_CHANGED" if status_changed else "REVIEWER_ASSIGNED", from_status=previous_status if status_changed else None, to_status=payload.status if status_changed else None, assigned_reviewer=case.assigned_reviewer))
    db.commit()
    return _response(_case_or_404(db, case.case_id))


@router.get("/{case_id}/evidence", response_model=list[EvidenceItemResponse], summary="List traceable, database-grounded evidence for a case")
def list_evidence(case_id: SafeId, db: Annotated[Session, Depends(get_db)]) -> list[EvidenceItemResponse]:
    case = _case_or_404(db, case_id)
    return [EvidenceItemResponse.model_validate(item) for item in sorted(case.evidence_items, key=lambda item: (item.retrieved_at, item.id))]
