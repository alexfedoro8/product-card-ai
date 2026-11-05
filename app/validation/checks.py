"""Проверки ответа модели (паттерн «Стратегия»).

Каждая проверка — отдельный класс с методом check(). Новая проверка добавляется
новым классом и строкой в default_checks(); генератор карточки не меняется.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.core.rules import DEFAULT_RULES, CardRules
from app.validation.base import CheckContext, DraftCheck
from app.validation.terms import FILLER_TERMS, INVENTED_SCOPE, RISKY_TERMS
from app.validation.text import find_absent_terms, find_ungrounded_numbers, numbers_in, numbers_missing_from


class LengthCheck:
    """Заголовок, слишком длинное описание, число запросов, коммерческий блок.

    Слишком короткое описание повтором не исправляем: просьба «допиши» порождает «воду».
    Об этом сообщает оценка данных (QualityAssessor).
    """

    def __init__(self, rules: CardRules = DEFAULT_RULES) -> None:
        self.rules = rules

    def check(self, ctx: CheckContext) -> list[str]:
        r, d = self.rules, ctx.draft
        issues: list[str] = []
        if not d.seo_title:
            issues.append("SEO-заголовок пустой.")
        elif len(d.seo_title) > r.title_max:
            issues.append(
                f"SEO-заголовок {len(d.seo_title)} символов, нужно не больше {r.title_max}. Сократи."
            )

        if len(d.seo_description) > r.description_max:
            issues.append(
                f"SEO-описание {len(d.seo_description)} символов, нужно "
                f"{r.description_min}–{r.description_max}. Сократи, убрав общие фразы."
            )

        count = len(d.search_queries)
        if not r.queries_min <= count <= r.queries_max:
            issues.append(f"Поисковых запросов {count}, нужно от {r.queries_min} до {r.queries_max} разных.")

        if not d.commercial_block:
            issues.append("Коммерческий блок пустой.")
        return issues


class GroundedNumbersCheck:
    """Каждое число в текстах модели должно быть во входных данных."""

    def check(self, ctx: CheckContext) -> list[str]:
        ungrounded = find_ungrounded_numbers(ctx.generated_text, ctx.source)
        if not ungrounded:
            return []
        return [
            "В тексте есть числа, которых нет во входных данных: "
            + ", ".join(ungrounded)
            + ". Убери их или замени значениями из входных данных."
        ]


class TermsCheck:
    """Термины из словаря, которых нет во входных данных: выдуманные свойства, сценарии, оценки."""

    def __init__(
        self, terms: Mapping[str, tuple[str, ...]], message: str, instruction: str = "Убери их."
    ) -> None:
        self.terms = terms
        self.message = message
        self.instruction = instruction

    def find(self, generated: str, source: str) -> list[str]:
        return find_absent_terms(self.terms, generated, source)

    def check(self, ctx: CheckContext) -> list[str]:
        found = self.find(ctx.generated_text, ctx.source)
        return [f"{self.message}: {', '.join(found)}. {self.instruction}"] if found else []


class ListFormatCheck:
    """Параметры в описании должны идти списком «- Название — значение»."""

    def __init__(self, rules: CardRules = DEFAULT_RULES) -> None:
        self.rules = rules

    @staticmethod
    def has_parameter_list(text: str) -> bool:
        return any(line.startswith("- ") for line in text.splitlines())

    def check(self, ctx: CheckContext) -> list[str]:
        if ctx.spec_count < self.rules.list_from_specs or self.has_parameter_list(ctx.draft.seo_description):
            return []
        return [
            "В SEO-описании параметры не оформлены списком. После вводного абзаца добавь строку "
            "«Основные характеристики:» и перечисли параметры, каждый с новой строки: "
            "«- Название — значение,»."
        ]


class ExtractionCoverageCheck:
    """Значения из описания не должны теряться: они либо в specs, либо в extracted_specs."""

    @staticmethod
    def find_lost(ctx: CheckContext) -> list[str]:
        covered = numbers_in(ctx.known) | numbers_in(" ".join(s.value for s in ctx.draft.extracted_specs))
        return numbers_missing_from(ctx.description, covered)

    def check(self, ctx: CheckContext) -> list[str]:
        if not ctx.description:
            return []
        lost = self.find_lost(ctx)
        if not lost:
            return []
        return [
            "В описании товара есть характеристики со значениями "
            + ", ".join(lost)
            + ", которых нет ни в specs, ни в extracted_specs. Вынеси каждую в extracted_specs "
            "с дословной цитатой из описания."
        ]


RISKY_CHECK = TermsCheck(RISKY_TERMS, "В тексте есть утверждения, которых нет во входных данных")
SCOPE_CHECK = TermsCheck(
    INVENTED_SCOPE,
    "В тексте есть области или сценарии применения, монтажа, эксплуатации, которых нет во входных данных",
)
FILLER_CHECK = TermsCheck(
    FILLER_TERMS,
    "В тексте есть оценочные или общие формулировки без опоры на данные",
    "Замени их фактами из входных данных или убери; если текст станет короче — это нормально.",
)


def default_checks(rules: CardRules = DEFAULT_RULES) -> list[DraftCheck]:
    return [
        LengthCheck(rules),
        ListFormatCheck(rules),
        GroundedNumbersCheck(),
        RISKY_CHECK,
        SCOPE_CHECK,
        FILLER_CHECK,
        ExtractionCoverageCheck(),
    ]
