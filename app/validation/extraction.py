"""Проверка значений, которые модель извлекла из текста описания."""

from __future__ import annotations

from app.schemas import ExtractedSpec
from app.validation.text import norm, numbers_in


def verify_extracted(
    extracted: list[ExtractedSpec], description: str
) -> tuple[list[ExtractedSpec], list[str]]:
    """Оставляет только значения, подтверждённые дословной цитатой из описания."""
    accepted: list[ExtractedSpec] = []
    rejected: list[str] = []
    desc = norm(description)

    for spec in extracted:
        if not spec.name or not spec.value:
            continue
        quote = norm(spec.source_quote)
        if not quote or quote not in desc:
            rejected.append(f"Значение «{spec.name}: {spec.value}» отброшено: цитата не найдена в описании.")
            continue
        if not numbers_in(spec.value) <= numbers_in(spec.source_quote):
            rejected.append(f"Значение «{spec.name}: {spec.value}» отброшено: числа не совпадают с цитатой.")
            continue
        accepted.append(spec)
    return accepted, rejected
