"""Компоновщик проверок: прогоняет ответ модели через набор стратегий."""

from __future__ import annotations

from collections.abc import Sequence

from app.validation.base import CheckContext, DraftCheck
from app.validation.checks import default_checks


class DraftValidator:
    def __init__(self, checks: Sequence[DraftCheck] | None = None) -> None:
        self.checks = list(checks) if checks is not None else default_checks()

    def validate(self, ctx: CheckContext) -> list[str]:
        """Все замечания по ответу модели. Пустой список — ответ принят."""
        return [issue for check in self.checks for issue in check.check(ctx)]
