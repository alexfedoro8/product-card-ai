"""Требования к карточке. Вынесены в один объект, чтобы их можно было поменять под другой магазин."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardRules:
    title_max: int = 70
    description_min: int = 800
    description_max: int = 1200
    queries_min: int = 3
    queries_max: int = 5
    # С какого числа характеристик параметры в описании должны идти списком
    list_from_specs: int = 2


DEFAULT_RULES = CardRules()
