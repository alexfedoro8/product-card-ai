"""Входные данные о товаре."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.core.normalize import normalize_specs

SpecValue = str | int | float | bool | None


class ProductInput(BaseModel):
    """Данные о приборе, которые присылает контент-менеджер или внешняя система."""

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
        # Структура входного JSON из текста задания — для подсказки в Swagger
        json_schema_extra={
            "examples": [
                {
                    "name": "Манометр показывающий DM 02",
                    "manufacturer": "Манотомь",
                    "specs": {
                        "диапазон измерений": "0–1,6 МПа",
                        "класс точности": "1,5",
                        "присоединение": "G1/2",
                        "диаметр корпуса": "100 мм",
                    },
                    "description": "Прибор предназначен для измерения избыточного давления...",
                }
            ]
        },
    )

    name: str = Field(..., min_length=1, max_length=300, description="Название товара")
    manufacturer: str | None = Field(None, max_length=200, description="Производитель")
    category: str | None = Field(None, max_length=200, description="Категория в каталоге")
    specs: dict[str, SpecValue] = Field(
        default_factory=dict, description="Характеристики: «название» → «значение»"
    )
    description: str | None = Field(
        None, max_length=20_000, description="Текстовое описание или фрагмент паспорта"
    )
    images: list[HttpUrl] = Field(
        default_factory=list,
        max_length=10,
        description="Ссылки на фото от производителя или загруженные через /api/v1/images (необязательно)",
    )

    @field_validator("manufacturer", "category", "description")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def has_some_data(self) -> ProductInput:
        clean_specs, _ = normalize_specs(self.specs)
        if not clean_specs and not self.description:
            raise ValueError(
                "нет ни заполненных характеристик, ни описания — недостаточно данных для карточки"
            )
        return self
