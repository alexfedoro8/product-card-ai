"""Замечания проверок написаны как инструкции модели; для человека их нужно переформулировать."""

from __future__ import annotations

import re

_MODEL_INSTRUCTION = re.compile(r"\.\s+(Убери|Сократи|Замени|Вынеси|Верни|Исправь)\b.*$", re.DOTALL)


def issue_for_user(issue: str) -> str:
    text = _MODEL_INSTRUCTION.sub(".", issue)
    return text.replace(
        "которых нет ни в specs, ни в extracted_specs", "которые не попали в таблицу характеристик"
    )
