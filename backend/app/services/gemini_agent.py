"""Controlled, tool-grounded Gemini investigation orchestration.

Gemini receives no database facts in its prompt.  It can obtain them only through
the allowlisted functions in this module, and its final JSON is validated before
it is saved or returned.
"""

import json
import importlib
import importlib.util
import logging
import time
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings
from app.models.device import Device
from app.models.dispute import Dispute
from app.models.risk_case import EvidenceItem, RiskCase
from app.models.transaction import Transaction
from app.schemas.api import InvestigationResponse

MAX_TOOL_ROUNDS = 8
logger = logging.getLogger("app.gemini")

TOOL_DECLARATIONS = [
    {"name": "get_transaction", "description": "Retrieve the case transaction from the synthetic database.", "parameters": {"type": "OBJECT", "properties": {}, "required": []}},
    {"name": "get_customer_history", "description": "Retrieve transaction history for the case customer.", "parameters": {"type": "OBJECT", "properties": {}, "required": []}},
    {"name": "get_previous_disputes", "description": "Retrieve prior disputes for the case customer.", "parameters": {"type": "OBJECT", "properties": {}, "required": []}},
    {"name": "get_device_history", "description": "Retrieve devices and related transactions for the case customer.", "parameters": {"type": "OBJECT", "properties": {}, "required": []}},
    {"name": "get_related_transactions", "description": "Retrieve recent transactions for the case merchant.", "parameters": {"type": "OBJECT", "properties": {}, "required": []}},
    {"name": "get_merchant_policy", "description": "Retrieve merchant policy evidence if present in the database.", "parameters": {"type": "OBJECT", "properties": {}, "required": []}},
    {"name": "create_evidence_report", "description": "Retrieve the already persisted, database-grounded evidence report for this case.", "parameters": {"type": "OBJECT", "properties": {}, "required": []}},
    {"name": "recommend_action", "description": "Record a bounded recommendation for human review only.", "parameters": {"type": "OBJECT", "properties": {"recommendation": {"type": "STRING", "enum": ["MANUAL_REVIEW", "GATHER_MORE_EVIDENCE", "CONTEST_DISPUTE"]}}, "required": ["recommendation"]}},
]


class GeminiAgentError(Exception):
    """Base controlled agent error safe to expose through the API."""


class GeminiAgentUnavailable(GeminiAgentError):
    """Gemini is not configured or failed before a valid answer was produced."""


class GeminiAgentResponseInvalid(GeminiAgentError):
    """Gemini output did not meet the strict application response contract."""


class GeminiInvestigationAgent:
    """Run a bounded Gemini tool-calling loop for one existing risk case."""

    def __init__(self, settings: Settings, client: Any | None = None, types_module: Any | None = None) -> None:
        self.settings = settings
        if not settings.gemini_api_key:
            raise GeminiAgentUnavailable("Gemini investigation is unavailable because GEMINI_API_KEY is not configured")
        if client is not None:
            self.client = client
            self.types = types_module
            return
        if importlib.util.find_spec("google.genai") is None:
            raise GeminiAgentUnavailable("Gemini investigation is unavailable because the backend Gemini dependency is not installed")
        genai = importlib.import_module("google.genai")
        self.types = importlib.import_module("google.genai.types")
        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=self.types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1000),
        )

    def investigate(self, case: RiskCase, db: Session) -> tuple[InvestigationResponse, list[dict[str, Any]]]:
        """Use only known tools, then validate output and evidence references."""
        contents: list[Any] = [
            self._prompt(case),
        ]
        tool_trace: list[dict[str, Any]] = []
        allowed_references: set[str] = set()
        for _ in range(MAX_TOOL_ROUNDS):
            response = self._generate_content(contents)
            function_calls = self._function_calls(response)
            if not function_calls:
                result = self._validated_result(self._response_text(response), allowed_references)
                return result, tool_trace
            tool_parts: list[Any] = []
            for name, arguments in function_calls:
                handler = self._tool_handlers(case, db).get(name)
                if handler is None:
                    raise GeminiAgentResponseInvalid(f"Gemini requested disallowed tool: {name}")
                tool_result = handler(arguments)
                references = tool_result.get("evidence_references", [])
                allowed_references.update(reference for reference in references if isinstance(reference, str))
                tool_trace.append({"tool_name": name, "arguments": arguments, "evidence_references": references})
                if self.types is None:
                    tool_parts.append({"function_response": {"name": name, "response": tool_result}})
                else:
                    tool_parts.append(self.types.Part.from_function_response(name=name, response=tool_result))
            contents.append({"role": "tool", "parts": tool_parts} if self.types is None else self.types.Content(role="tool", parts=tool_parts))
        raise GeminiAgentResponseInvalid("Gemini exceeded the maximum permitted tool-call rounds")

    def _generate_content(self, contents: list[Any]) -> Any:
        attempts = self.settings.gemini_max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                return self.client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=contents,
                    config={"tools": [{"function_declarations": TOOL_DECLARATIONS}]} if self.types is None else self.types.GenerateContentConfig(tools=[{"function_declarations": TOOL_DECLARATIONS}]),
                )
            except Exception as exc:  # Provider/network failures must not affect ML predictions.
                logger.warning(
                    "gemini_generate_content_failed",
                    extra={"attempt": attempt, "max_attempts": attempts, "model": self.settings.gemini_model},
                )
                if attempt >= attempts:
                    raise GeminiAgentUnavailable("Gemini investigation is temporarily unavailable") from exc
                time.sleep(min(0.25 * attempt, 1.0))
        raise GeminiAgentUnavailable("Gemini investigation is temporarily unavailable")

    @staticmethod
    def _function_calls(response: Any) -> list[tuple[str, dict[str, Any]]]:
        calls: list[tuple[str, dict[str, Any]]] = []
        for candidate in getattr(response, "candidates", []) or []:
            for part in getattr(getattr(candidate, "content", None), "parts", []) or []:
                function_call = getattr(part, "function_call", None)
                if function_call:
                    calls.append((function_call.name, dict(function_call.args or {})))
        return calls

    @staticmethod
    def _response_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise GeminiAgentResponseInvalid("Gemini returned no structured investigation result")
        return text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    @staticmethod
    def _validated_result(raw_json: str, allowed_references: set[str]) -> InvestigationResponse:
        try:
            result = InvestigationResponse.model_validate_json(raw_json)
        except ValidationError as exc:
            raise GeminiAgentResponseInvalid("Gemini returned an invalid investigation result") from exc
        if not set(result.evidence_references).issubset(allowed_references):
            raise GeminiAgentResponseInvalid("Gemini cited evidence that was not returned by a tool")
        return result

    @staticmethod
    def _prompt(case: RiskCase) -> str:
        return (
            "You are a synthetic-demo chargeback investigation assistant. You are not the risk model and cannot execute financial actions. "
            f"The independently computed ML result is risk_score={case.risk_score}, risk_level={case.risk_level}. "
            "Retrieve factual evidence with tools before answering. Call create_evidence_report and cite only evidence IDs returned by tools. "
            "Return JSON only: risk_summary, evidence_references, risk_factors, recommendation, confidence, requires_human_review. "
            "requires_human_review must be true; recommendation must be MANUAL_REVIEW, GATHER_MORE_EVIDENCE, or CONTEST_DISPUTE."
        )

    def _tool_handlers(self, case: RiskCase, db: Session) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        transaction = db.scalar(select(Transaction).options(joinedload(Transaction.customer), joinedload(Transaction.merchant)).where(Transaction.id == case.transaction_id))
        if transaction is None:
            raise GeminiAgentResponseInvalid("The case transaction is no longer available")

        def evidence_references(*evidence_types: str) -> list[str]:
            rows = db.scalars(select(EvidenceItem).where(EvidenceItem.risk_case_id == case.id, EvidenceItem.evidence_type.in_(evidence_types))).all()
            return [row.id for row in rows]

        def get_transaction(_: dict[str, Any]) -> dict[str, Any]:
            return {"transaction_id": transaction.transaction_id, "amount": str(transaction.amount), "currency": transaction.currency, "status": transaction.status, "evidence_references": evidence_references("transaction", "risk_prediction")}

        def get_customer_history(_: dict[str, Any]) -> dict[str, Any]:
            rows = db.scalars(select(Transaction).where(Transaction.customer_id == transaction.customer_id).order_by(Transaction.created_at.desc())).all()
            return {"customer_id": transaction.customer_id, "transaction_count": len(rows), "transactions": [{"transaction_id": row.transaction_id, "amount": str(row.amount), "status": row.status} for row in rows], "evidence_references": evidence_references("customer")}

        def get_previous_disputes(_: dict[str, Any]) -> dict[str, Any]:
            rows = db.scalars(select(Dispute).where(Dispute.customer_id == transaction.customer_id).order_by(Dispute.created_at.desc())).all()
            return {"customer_id": transaction.customer_id, "disputes": [{"id": row.id, "reason_code": row.reason_code, "status": row.status} for row in rows], "evidence_references": evidence_references("dispute")}

        def get_device_history(_: dict[str, Any]) -> dict[str, Any]:
            rows = db.scalars(select(Device).where(Device.customer_id == transaction.customer_id)).all()
            return {"customer_id": transaction.customer_id, "devices": [{"id": row.id, "fingerprint": row.fingerprint} for row in rows], "evidence_references": evidence_references("device")}

        def get_related_transactions(_: dict[str, Any]) -> dict[str, Any]:
            rows = db.scalars(select(Transaction).where(Transaction.merchant_id == transaction.merchant_id).order_by(Transaction.created_at.desc()).limit(50)).all()
            return {"merchant_id": transaction.merchant_id, "transactions": [{"transaction_id": row.transaction_id, "amount": str(row.amount), "status": row.status} for row in rows], "evidence_references": evidence_references("merchant")}

        def get_merchant_policy(_: dict[str, Any]) -> dict[str, Any]:
            return {"availability": "Evidence unavailable", "reason": "No merchant policy record exists in the synthetic demo schema", "evidence_references": evidence_references("merchant")}

        def create_evidence_report(_: dict[str, Any]) -> dict[str, Any]:
            rows = db.scalars(select(EvidenceItem).where(EvidenceItem.risk_case_id == case.id).order_by(EvidenceItem.retrieved_at, EvidenceItem.id)).all()
            return {"evidence": [{"id": row.id, "type": row.evidence_type, "content": row.factual_content, "verification_status": row.verification_status} for row in rows], "evidence_references": [row.id for row in rows]}

        def recommend_action(arguments: dict[str, Any]) -> dict[str, Any]:
            recommendation = arguments.get("recommendation")
            if recommendation not in {"MANUAL_REVIEW", "GATHER_MORE_EVIDENCE", "CONTEST_DISPUTE"}:
                raise GeminiAgentResponseInvalid("Gemini requested an invalid recommendation")
            return {"recommendation": recommendation, "requires_human_review": True, "financial_action_executed": False, "evidence_references": []}

        return {"get_transaction": get_transaction, "get_customer_history": get_customer_history, "get_previous_disputes": get_previous_disputes, "get_device_history": get_device_history, "get_related_transactions": get_related_transactions, "get_merchant_policy": get_merchant_policy, "create_evidence_report": create_evidence_report, "recommend_action": recommend_action}


def serialize_investigation(result: InvestigationResponse, tool_trace: list[dict[str, Any]]) -> tuple[str, str, str]:
    """Serialize validated values only for the audit record."""
    return json.dumps(tool_trace), json.dumps(result.evidence_references), result.model_dump_json()
