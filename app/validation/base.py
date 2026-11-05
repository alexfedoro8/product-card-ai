"""Контракт проверки ответа модели."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas import LLMDraft


@dataclass(frozen=True)
class CheckContext:
    """Всё, что нужно проверкам: ответ модели и входные данные в удобном виде."""

    draft: LLMDraft
    source: str  # все входные данные одной строкой
    description: str = ""  # текст описания товара
    known: str = ""  # название и характеристики (ключи и значения)
    spec_count: int = 0

    @property
    def generated_text(self) -> str:
        """Все тексты, которые увидит покупатель или менеджер."""
        d = self.draft
        return "\n".join([d.seo_title, d.seo_description, d.commercial_block, *d.search_queries])


class DraftCheck(Protocol):
    """Одна проверка. Возвращает замечания в виде инструкций для модели; пустой список — всё хорошо."""

    def check(self, ctx: CheckContext) -> list[str]: ...
