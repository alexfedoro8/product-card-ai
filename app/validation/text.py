"""Утилиты сравнения текста модели с входными данными."""

from __future__ import annotations

import re
from collections.abc import Mapping

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def norm(text: str) -> str:
    """Нижний регистр, «ё» → «е», все тире → «-», схлопнутые пробелы."""
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[‐‑‒–—−]", "-", text)
    text = text.replace(" ", " ")
    return " ".join(text.split())


def norm_number(token: str) -> str:
    value = float(token.replace(",", "."))
    return f"{value:f}".rstrip("0").rstrip(".") or "0"


def numbers_in(text: str) -> set[str]:
    """Нормализованные числа в тексте: «1,6» и «1.60» дают одно и то же «1.6»."""
    return {norm_number(m) for m in NUMBER_RE.findall(text)}


def numbers_missing_from(text: str, reference: set[str]) -> list[str]:
    """Числа из text (в исходном написании), которых нет в reference."""
    found: list[str] = []
    for token in NUMBER_RE.findall(text):
        if norm_number(token) not in reference and token not in found:
            found.append(token)
    return found


def find_ungrounded_numbers(generated: str, source: str) -> list[str]:
    return numbers_missing_from(generated, numbers_in(source))


def find_absent_terms(terms: Mapping[str, tuple[str, ...]], generated: str, source: str) -> list[str]:
    """Метки терминов, которые есть в тексте модели, но отсутствуют во входных данных."""
    gen, src = norm(generated), norm(source)
    return [
        label
        for label, stems in terms.items()
        if any(s in gen for s in stems) and not any(s in src for s in stems)
    ]
