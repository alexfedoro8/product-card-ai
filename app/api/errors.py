"""Обработчики ошибок: единый формат ErrorResponse и понятные сообщения на русском."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.schemas import ErrorResponse

VALIDATION_MESSAGES = {
    "missing": "обязательное поле не передано",
    "string_type": "ожидается строка",
    "string_too_short": "поле не должно быть пустым",
    "string_too_long": "слишком длинное значение",
    "dict_type": 'ожидается объект вида {"название": "значение"}',
    "list_type": "ожидается список",
    "too_long": "слишком много элементов",
    "url_parsing": "некорректная ссылка",
    "url_scheme": "ссылка должна начинаться с http:// или https://",
    "model_attributes_type": "ожидается JSON-объект",
}


def describe_validation_error(error: dict[str, Any]) -> str:
    loc = [str(p) for p in error.get("loc", ()) if p != "body"]
    if error.get("type") == "json_invalid":
        position = error.get("loc", ("body", "?"))[-1]
        reason = (error.get("ctx") or {}).get("error", "")
        return f"Некорректный JSON (позиция {position}): {reason}".strip()
    message = VALIDATION_MESSAGES.get(error.get("type", ""), str(error.get("msg", "")))
    message = message.removeprefix("Value error, ")
    return f"Поле «{'.'.join(loc)}»: {message}" if loc else message


def error_response(status: int, code: str, message: str, details: list[str] | None = None) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, details=details or [])
    return JSONResponse(status_code=status, content=body.model_dump())


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [describe_validation_error(e) for e in exc.errors()]
    return error_response(422, "invalid_input", "Входные данные некорректны", details)


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc.http_status, exc.code, exc.message)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(AppError, app_error_handler)
