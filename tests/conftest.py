"""Общие фикстуры: фейковый LLM-клиент и типовые ответы модели."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas import ProductInput  # noqa: E402
from app.services import CardGenerator  # noqa: E402

FILLER = "Диапазон измерений 0–1,6 МПа, класс точности 1,5, присоединение G1/2, диаметр корпуса 100 мм. "


class FakeLLM:
    """Возвращает заранее заданные ответы по очереди (последний — повторяет) и запоминает запросы."""

    model = "fake-model"

    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]], temperature: float) -> str:
        self.calls.append(messages)
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


def make_draft(
    *,
    title: str = "Манометр DM 02 0–1,6 МПа G1/2 класс 1,5",
    description_len: int = 1000,
    extra: str = "",
    queries: list[str] | None = None,
    extracted: list[dict[str, str]] | None = None,
    as_list: bool = True,
) -> str:
    base = "Манометр показывающий DM 02 с диапазоном 0–1,6 МПа и присоединением G1/2. " + extra
    params = (
        "\n\nОсновные характеристики:\n- Диапазон измерений — 0–1,6 МПа,\n- Присоединение — G1/2."
        if as_list
        else ""
    )
    description = (base + FILLER * 20)[: max(description_len - len(params), 0)].strip() + params
    return json.dumps(
        {
            "seo_title": title,
            "seo_description": description,
            "search_queries": queries
            if queries is not None
            else ["манометр dm 02", "манометр 1,6 мпа g1/2", "купить манометр dm 02"],
            "commercial_block": "Подходит службам КИПиА для контроля давления.",
            # по умолчанию — значение из описания фикстуры dm02, подтверждённое цитатой
            "extracted_specs": extracted
            if extracted is not None
            else [
                {"name": "степень защиты", "value": "IP40", "source_quote": "Степень защиты корпуса — IP40"}
            ],
        },
        ensure_ascii=False,
    )


@pytest.fixture
def dm02() -> ProductInput:
    return ProductInput.model_validate(
        {
            "name": "Манометр показывающий DM 02",
            "manufacturer": "Манотомь",
            "specs": {
                "диапазон измерений": "0–1,6 МПа",
                "класс точности": "1,5",
                "присоединение": "G1/2",
                "диаметр корпуса": "100 мм",
            },
            "description": "Прибор предназначен для измерения избыточного давления. "
            "Степень защиты корпуса — IP40.",
        }
    )


def generate(product: ProductInput, llm: FakeLLM, **kwargs: object):
    """Карточка через CardGenerator с фейковой моделью."""
    return CardGenerator(llm, **kwargs).generate(product)  # type: ignore[arg-type]
