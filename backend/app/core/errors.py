"""Consistent API error response helpers."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """Stable error response format for every API error."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"detail": "Not found", "code": "not_found"}]})

    detail: str
    code: str


def error_response(status_code: int, detail: str, code: str) -> JSONResponse:
    """Build a JSON error response using the project-wide contract."""
    return JSONResponse(status_code=status_code, content=ErrorResponse(detail=detail, code=code).model_dump())


def register_error_handlers(app: FastAPI) -> None:
    """Register exception handlers that preserve the stable error contract."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:  # noqa: ARG001
        code = "http_error"
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return error_response(exc.status_code, detail, code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # noqa: ARG001
        return error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, "Request validation failed", "validation_error")
