"""Результат: черновик карточки товара и оценка данных."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SpecRow(BaseModel):
    name: str
    value: str
    source: Literal["входные данные", "описание"] = Field(
        description="Откуда взято значение: из характеристик или из текста описания"
    )
    quote: str | None = Field(None, description="Цитата из описания, подтверждающая значение")


class MissingField(BaseModel):
    name: str
    value: Literal["данных нет"] = Field("данных нет", description="Пометка для отсутствующей характеристики")
    reason: str


class RequirementCheck(BaseModel):
    """Соответствие результата одному требованию к карточке."""

    name: str
    ok: bool
    value: str = Field(description="Фактическое значение, например «420 символов»")
    hint: str | None = Field(None, description="Что дать на вход, чтобы требование выполнилось")


class DataQuality(BaseModel):
    """Оценка введённых данных: соответствует ли карточка требованиям и что дополнить."""

    level: Literal["good", "gaps", "poor"] = Field(
        description="good — требования выполнены; gaps — стоит уточнить данные; "
        "poor — часть требований не выполнена из-за нехватки данных"
    )
    label: str
    facts_count: int = Field(description="Характеристик в таблице (из входа и подтверждённых из описания)")
    gaps_count: int = Field(description="Полей, требующих уточнения (без учёта фото)")
    requirements: list[RequirementCheck]
    how_to_improve: list[str] = Field(description="Какие данные добавить, чтобы улучшить карточку")


class CardMeta(BaseModel):
    model: str
    attempts: int
    device_type: str


class CardResponse(BaseModel):
    """Черновик карточки товара."""

    name: str
    manufacturer: str | None
    category: str | None
    seo_title: str
    seo_title_length: int
    seo_description: str
    seo_description_length: int
    key_specs: list[SpecRow]
    search_queries: list[str]
    commercial_block: str
    images: list[str]
    missing_fields: list[MissingField]
    data_quality: DataQuality
    warnings: list[str] = Field(
        description="Замечания проверки сгенерированного текста, которые модель не устранила за все попытки"
    )
    markdown: str = ""
    meta: CardMeta
