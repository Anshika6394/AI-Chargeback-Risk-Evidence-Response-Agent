"""Pydantic contracts for the documented Phase 5 REST API."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SafeId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
CountryCode = Annotated[str, StringConstraints(to_upper=True, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")]


class RiskPredictRequest(BaseModel):
    """Model-ready transaction features, supplied with an existing transaction ID for audit."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"transaction_id": "synthetic_phase2_txn_0000", "amount": 450.0, "amount_deviation": 2.1, "transaction_velocity_24h": 3, "transaction_velocity_7d": 12, "customer_account_age_days": 180, "customer_dispute_count": 1, "customer_refund_count": 0, "customer_failed_tx_count": 1, "device_age_days": 21, "dispute_ratio": 0.08, "refund_ratio": 0.0, "has_device": 1, "is_new_device": 0, "currency": "INR", "status": "captured", "payment_method": "card", "merchant_category": "electronics", "customer_country": "IN", "merchant_country": "IN", "transaction_hour_bucket": "afternoon", "transaction_day_of_week": "Friday", "location_match": "match"}]})
    transaction_id: SafeId
    amount: float = Field(ge=0, le=10_000_000)
    amount_deviation: float = Field(ge=0, le=1_000_000)
    transaction_velocity_24h: int = Field(ge=0, le=100_000)
    transaction_velocity_7d: int = Field(ge=0, le=1_000_000)
    customer_account_age_days: int = Field(ge=0, le=100_000)
    customer_dispute_count: int = Field(ge=0, le=100_000)
    customer_refund_count: int = Field(ge=0, le=100_000)
    customer_failed_tx_count: int = Field(ge=0, le=100_000)
    device_age_days: int = Field(ge=0, le=100_000)
    dispute_ratio: float = Field(ge=0, le=1)
    refund_ratio: float = Field(ge=0, le=1)
    has_device: Literal[0, 1]
    is_new_device: Literal[0, 1]
    currency: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3, to_upper=True)]
    status: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    payment_method: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    merchant_category: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    customer_country: CountryCode
    merchant_country: CountryCode
    transaction_hour_bucket: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    transaction_day_of_week: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    location_match: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class RiskFactorResponse(BaseModel):
    transformed_feature: str
    source_feature: str
    feature_value: float
    contribution: float
    attribution_method: str


class RiskPredictResponse(BaseModel):
    prediction_id: str
    transaction_id: str
    probability: float
    risk_score: int
    risk_level: str
    model_version: str
    model_derived_risk_factors: list[RiskFactorResponse]


class TransactionListItem(BaseModel):
    transaction_id: str
    customer_id: str
    merchant_id: str
    amount: Decimal
    currency: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PageResponse(BaseModel):
    items: list[TransactionListItem]
    page: int
    page_size: int
    total: int


class TransactionDetailResponse(TransactionListItem):
    id: str
    device_id: str | None
    updated_at: datetime
    customer_email: str
    customer_name: str
    merchant_name: str
    merchant_category: str
    disputes_count: int


class CustomerHistoryResponse(BaseModel):
    customer_id: str
    transaction_count: int
    total_amount: Decimal
    average_amount: Decimal
    disputed_transaction_count: int
    transactions: list[TransactionListItem]


class DisputeResponse(BaseModel):
    id: str
    transaction_id: str
    reason_code: str
    status: str
    evidence_summary: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskSummaryResponse(BaseModel):
    total_transactions: int
    total_predictions: int
    risk_level_counts: dict[str, int]
    average_risk_score: float | None


class ModelMetricsResponse(BaseModel):
    model_version: str
    model_type: str
    dataset_version: str
    evaluated_at: datetime
    metrics: dict[str, object]


class ModelInfoResponse(BaseModel):
    model_version: str
    model_type: str
    dataset_version: str
    feature_count: int
    selection_criterion: str
    held_out_test_policy: str
