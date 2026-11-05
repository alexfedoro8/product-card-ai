"""Генерация карточки (паттерн «Фасад»).

CardGenerator связывает шаги: подготовка данных → модель → проверки → повтор с обратной
связью → сборка результата. Все зависимости приходят через конструктор (Dependency
Injection): клиент модели, набор проверок, оценщик, рендерер можно заменить, не меняя класс.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import LLMError
from app.core.normalize import clean_text, normalize_specs
from app.llm.base import ChatMessage, LLMClient
from app.schemas import CardMeta, CardResponse, LLMDraft, ProductInput
from app.services.checklist import DeviceProfile, detect_device_type, find_missing
from app.services.parsing import DraftParseError, parse_draft
from app.services.prompts import PromptBuilder
from app.services.quality import QualityAssessor
from app.services.rendering import CardRenderer, MarkdownRenderer
from app.services.specs import build_missing, build_spec_rows
from app.validation import CheckContext, DraftValidator, issue_for_user, verify_extracted


@dataclass(frozen=True)
class PreparedInput:
    """Входные данные после очистки — то, с чем работают промпт и проверки."""

    product: ProductInput
    specs: dict[str, str]
    empty_fields: list[str]
    description: str
    profile: DeviceProfile

    @property
    def source(self) -> str:
        """Все входные данные одной строкой — эталон для проверки «выдуманных» фактов."""
        p = self.product
        parts = [p.name, p.manufacturer or "", p.category or "", self.description]
        parts += [f"{k}: {v}" for k, v in self.specs.items()]
        return "\n".join(parts)

    @property
    def known(self) -> str:
        return "\n".join([self.product.name, *self.specs.keys(), *self.specs.values()])

    @classmethod
    def from_product(cls, product: ProductInput) -> PreparedInput:
        specs, empty = normalize_specs(product.specs)
        return cls(
            product=product,
            specs=specs,
            empty_fields=empty,
            description=clean_text(product.description or ""),
            profile=detect_device_type(product.name, product.category),
        )


@dataclass
class DraftResult:
    draft: LLMDraft
    issues: list[str]
    attempts: int


class CardGenerator:
    def __init__(
        self,
        client: LLMClient,
        *,
        prompts: PromptBuilder | None = None,
        validator: DraftValidator | None = None,
        assessor: QualityAssessor | None = None,
        renderer: CardRenderer | None = None,
        max_attempts: int = 3,
        temperature: float = 0.3,
    ) -> None:
        self.client = client
        self.prompts = prompts or PromptBuilder()
        self.validator = validator or DraftValidator()
        self.assessor = assessor or QualityAssessor()
        self.renderer = renderer or MarkdownRenderer()
        self.max_attempts = max_attempts
        self.temperature = temperature

    def generate(self, product: ProductInput) -> CardResponse:
        data = PreparedInput.from_product(product)
        result = self._draft_with_retries(data)
        card = self._assemble(data, result)
        return card.model_copy(update={"markdown": self.renderer.render(card)})

    # --- шаг 1–3: модель, проверки, повтор с обратной связью -------------------------------

    def _draft_with_retries(self, data: PreparedInput) -> DraftResult:
        # Поля, переданные пустыми, тоже «известны как отсутствующие» — не дублируем их в списке.
        missing = find_missing(data.profile, [*data.specs, *data.empty_fields]) + data.empty_fields
        messages: list[ChatMessage] = self.prompts.initial_messages(
            data.product, data.specs, data.description, data.profile.title, missing
        )

        best: DraftResult | None = None
        for attempt in range(1, self.max_attempts + 1):
            raw = self.client.complete(messages, self.temperature)
            try:
                draft = parse_draft(raw)
            except DraftParseError as exc:
                issues = [f"Ответ не соответствует формату: {exc}. Верни только JSON."]
            else:
                issues = self.validator.validate(self._context(data, draft))
                if best is None or len(issues) < len(best.issues):
                    best = DraftResult(draft, issues, attempt)
                if not issues:
                    break
            messages = [*messages, {"role": "assistant", "content": raw}, self.prompts.retry_message(issues)]

        if best is None:
            raise LLMError(
                f"Модель не вернула ответ в нужном формате за {self.max_attempts} попытки. Повторите запрос.",
                code="llm_bad_format",
            )
        best.attempts = attempt
        return best

    @staticmethod
    def _context(data: PreparedInput, draft: LLMDraft) -> CheckContext:
        return CheckContext(
            draft=draft,
            source=data.source,
            description=data.description,
            known=data.known,
            spec_count=len(data.specs),
        )

    # --- шаг 4: сборка карточки кодом ---------------------------------------------------------

    def _assemble(self, data: PreparedInput, result: DraftResult) -> CardResponse:
        draft, product = result.draft, data.product
        accepted, rejected = verify_extracted(draft.extracted_specs, data.description)
        rows = build_spec_rows(product, data.specs, accepted)
        missing = build_missing(product, data.profile, rows, data.empty_fields, data.description)

        return CardResponse(
            name=product.name,
            manufacturer=product.manufacturer,
            category=product.category,
            seo_title=draft.seo_title,
            seo_title_length=len(draft.seo_title),
            seo_description=draft.seo_description,
            seo_description_length=len(draft.seo_description),
            key_specs=rows,
            search_queries=draft.search_queries,
            commercial_block=draft.commercial_block,
            images=[str(url) for url in product.images],
            missing_fields=missing,
            data_quality=self.assessor.assess(
                draft, rows, missing, text_has_issues=bool(result.issues), has_images=bool(product.images)
            ),
            warnings=[*map(issue_for_user, result.issues), *rejected],
            meta=CardMeta(model=self.client.model, attempts=result.attempts, device_type=data.profile.title),
        )
