"""Единый формат ошибки API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[str] = Field(default_factory=list)
