"""Разбор ответа модели в LLMDraft."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.schemas import LLMDraft


class DraftParseError(ValueError):
    pass


def parse_draft(raw: str) -> LLMDraft:
    """Извлекает JSON из ответа (в том числе из ```json-блока) и проверяет схему."""
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise DraftParseError("в ответе нет JSON-объекта")
    try:
        return LLMDraft.model_validate(json.loads(text[start : end + 1]))
    except json.JSONDecodeError as exc:
        raise DraftParseError(f"некорректный JSON: {exc.msg}") from exc
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
        raise DraftParseError(f"не хватает или неверны поля: {fields}") from exc
