"""Pydantic-схемы: вход, ответ модели, результат и ошибки."""

from app.schemas.card import CardMeta, CardResponse, DataQuality, MissingField, RequirementCheck, SpecRow
from app.schemas.errors import ErrorResponse
from app.schemas.llm import ExtractedSpec, LLMDraft
from app.schemas.product import ProductInput, SpecValue

__all__ = [
    "CardMeta",
    "CardResponse",
    "DataQuality",
    "ErrorResponse",
    "ExtractedSpec",
    "LLMDraft",
    "MissingField",
    "ProductInput",
    "RequirementCheck",
    "SpecRow",
    "SpecValue",
]
