"""Оценка введённых данных: соответствие требованиям и что дополнить."""

from __future__ import annotations

from app.core.rules import DEFAULT_RULES, CardRules
from app.schemas import DataQuality, LLMDraft, MissingField, RequirementCheck, SpecRow
from app.services.specs import DESCRIPTION_FIELD, PHOTO_FIELD

MORE_FACTS = "нужно больше фактов на входе: характеристики, текст описания или паспорта"
PASSPORT_TIP = (
    "Вставьте в поле «Описание» текст из паспорта или руководства по эксплуатации — "
    "сервис сам вынесет из него характеристики в таблицу и сможет написать полное описание."
)


class QualityAssessor:
    """Не все требования выполнимы при бедных входных данных — это нормально:
    сервис не добирает объём выдумками, а говорит, какой информации не хватает.
    """

    def __init__(self, rules: CardRules = DEFAULT_RULES) -> None:
        self.rules = rules

    def assess(
        self,
        draft: LLMDraft,
        rows: list[SpecRow],
        missing: list[MissingField],
        *,
        text_has_issues: bool,
        has_images: bool,
    ) -> DataQuality:
        gaps = [m for m in missing if m.name not in {PHOTO_FIELD, DESCRIPTION_FIELD}]
        has_description = all(m.name != DESCRIPTION_FIELD for m in missing)
        desc_short = len(draft.seo_description) < self.rules.description_min

        return DataQuality(
            level=self._level(desc_short, gaps),
            label=self._label(desc_short, gaps),
            facts_count=len(rows),
            gaps_count=len(gaps),
            requirements=self._requirements(draft, rows, gaps, text_has_issues, has_images),
            how_to_improve=self._tips(gaps, desc_short, has_description, has_images),
        )

    @staticmethod
    def _level(desc_short: bool, gaps: list[MissingField]) -> str:
        return "poor" if desc_short else ("gaps" if gaps else "good")

    @staticmethod
    def _label(desc_short: bool, gaps: list[MissingField]) -> str:
        if desc_short:
            return (
                "Карточка сформирована по имеющимся данным, "
                "но часть требований не выполнена — нужно больше информации"
            )
        if gaps:
            return "Карточка готова, но часть данных стоит уточнить"
        return "Карточка соответствует требованиям"

    def _requirements(
        self,
        draft: LLMDraft,
        rows: list[SpecRow],
        gaps: list[MissingField],
        text_has_issues: bool,
        has_images: bool,
    ) -> list[RequirementCheck]:
        r = self.rules
        title_len, desc_len = len(draft.seo_title), len(draft.seo_description)
        queries = len(draft.search_queries)
        gap_names = ", ".join(m.name for m in gaps)
        if desc_len < r.description_min:
            desc_hint: str | None = MORE_FACTS
        elif desc_len > r.description_max:
            desc_hint = "сократите вручную"
        else:
            desc_hint = None

        return [
            RequirementCheck(
                name=f"SEO-заголовок до {r.title_max} символов",
                ok=0 < title_len <= r.title_max,
                value=f"{title_len} симв.",
                hint=None if title_len <= r.title_max else "модель не уложилась — сократите вручную",
            ),
            RequirementCheck(
                name=f"SEO-описание {r.description_min}–{r.description_max} символов",
                ok=r.description_min <= desc_len <= r.description_max,
                value=f"{desc_len} симв.",
                hint=desc_hint,
            ),
            RequirementCheck(
                name="Характеристики без пробелов",
                ok=not gaps,
                value=f"{len(rows)} в таблице, уточнить: {len(gaps)}",
                hint=f"дополните: {gap_names}" if gaps else None,
            ),
            RequirementCheck(
                name=f"Поисковые запросы: {r.queries_min}–{r.queries_max}",
                ok=r.queries_min <= queries <= r.queries_max,
                value=str(queries),
            ),
            RequirementCheck(name="Коммерческий блок", ok=bool(draft.commercial_block), value="есть"),
            RequirementCheck(
                name="Фото товара",
                ok=has_images,
                value="есть" if has_images else "нет",
                hint=None if has_images else "загрузите файл или вставьте ссылку",
            ),
            RequirementCheck(
                name="Технические значения только из входных данных",
                ok=not text_has_issues,
                value="есть замечания" if text_has_issues else "проверено",
                hint="см. замечания проверки текста ниже" if text_has_issues else None,
            ),
        ]

    @staticmethod
    def _tips(
        gaps: list[MissingField], desc_short: bool, has_description: bool, has_images: bool
    ) -> list[str]:
        tips: list[str] = []
        if gaps:
            tips.append(f"Добавьте в форму характеристики: {', '.join(m.name for m in gaps)}.")
        if desc_short or gaps or not has_description:
            tips.append(("Описание не передано. " if not has_description else "") + PASSPORT_TIP)
        if not has_images:
            tips.append("Приложите фото товара файлом или ссылкой от производителя.")
        return tips
