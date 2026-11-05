"""Очистка входных данных до передачи в модель."""

from __future__ import annotations

from collections.abc import Mapping

# Значения, которые означают «характеристики нет», хотя поле формально заполнено.
EMPTY_MARKERS = {
    "",
    "-",
    "—",
    "–",
    "?",
    "н/д",
    "нд",
    "нет данных",
    "данных нет",
    "не указано",
    "уточняется",
    "null",
    "none",
    "n/a",
}


def clean_text(value: object) -> str:
    """Схлопывает пробелы и переносы строк."""
    return " ".join(str(value).split())


def capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _value_to_str(value: object) -> str:
    if isinstance(value, bool):
        return "да" if value else "нет"
    return clean_text(value)


def normalize_specs(specs: Mapping[str, object]) -> tuple[dict[str, str], list[str]]:
    """Возвращает (заполненные характеристики, названия полей, переданных пустыми).

    Ключи приводятся к виду «С заглавной буквы», дубликаты без учёта регистра
    отбрасываются (остаётся первое значение).
    """
    clean: dict[str, str] = {}
    empty: list[str] = []
    seen: set[str] = set()

    for raw_key, raw_value in specs.items():
        key = capitalize(clean_text(raw_key))
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())

        value = "" if raw_value is None else _value_to_str(raw_value)
        if value.lower() in EMPTY_MARKERS:
            empty.append(key)
        else:
            clean[key] = value

    return clean, empty
